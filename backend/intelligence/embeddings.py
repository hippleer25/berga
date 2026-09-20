"""
intelligence/embeddings.py — Embedding model and Qdrant client singletons.

Thread-safe initialisation with double-checked locking.

Runtime backend: zero-copy numpy inference over the StaticEmbedding
weights (safetensors mmap + HF `tokenizers`).

  – No PyTorch, no transformers, no sentence-transformers at runtime.
    (StaticEmbedding = bag-of-token-embeddings: the "model" is a lookup
    table plus a mean — numpy does the entire forward pass.)
  – Weights are np.memmap'd, so RSS cost is only the pages actually
    touched (shared, evictable), not the full 434 MB file.
  – Floor RSS for the whole pipeline measured at ~57 MB
    (the previous torch pipeline peaked at 428 MB).
  – Output parity with the torch pipeline is bit-exact on the
    validation probes (cosine 1.000); see AGENTS.md history.
"""

from __future__ import annotations

import html
import hashlib
import json
import logging
import os
import re
import struct
import threading
import uuid
from pathlib import Path
from typing import Optional

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import (
    Distance,
    PointStruct,
    ScalarQuantization,
    ScalarQuantizationConfig,
    ScalarType,
    VectorParams,
)

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

MODEL_NAME: str = os.environ.get("EMBEDDING_MODEL_NAME", "")
if not MODEL_NAME:
    raise RuntimeError(
        "EMBEDDING_MODEL_NAME environment variable is required. "
        "Example: sentence-transformers/static-similarity-mrl-multilingual-v1"
    )

COLLECTION_NAME: str = os.environ.get("QDRANT_COLLECTION_NAME", "feed_items")
TAG_PHRASES_COLLECTION: str = os.environ.get("QDRANT_TAG_PHRASES_COLLECTION", "tag_phrases")
VECTOR_SIZE: int = int(os.environ.get("VECTOR_SIZE", 256))

EMBEDDING_DESCRIPTION_CHARS: int = int(os.environ.get("EMBEDDING_DESCRIPTION_CHARS", "200"))

_DISTANCE_STR = os.environ.get("DISTANCE_METRIC", "Cosine").upper()
try:
    DISTANCE_METRIC = Distance[_DISTANCE_STR]
except KeyError:
    raise ValueError(
        f"Invalid DISTANCE_METRIC '{_DISTANCE_STR}'. "
        f"Valid options: {', '.join(d.name for d in Distance)}"
    )

# Model repo layout (StaticEmbedding models): a single safetensors weights
# file plus a fast-tokenizer JSON. No ONNX export is required — numpy
# reproduces the entire forward pass.
_SAFETENSORS_RELPATH = "0_StaticEmbedding/model.safetensors"
_TOKENIZER_RELPATH = "0_StaticEmbedding/tokenizer.json"
_SAFETENSORS_DTYPE_MAP = {
    "F64": np.float64,
    "F32": np.float32,
    "F16": np.float16,
    "BF16": None,  # numpy has no bfloat16 — rejected at load time
    "I8": np.int8,
    "I16": np.int16,
    "I32": np.int32,
    "I64": np.int64,
    "U8": np.uint8,
    "BOOL": np.bool_,
}

# ── Embedding text builder ────────────────────────────────────────────────────

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_ENTITY_RE = re.compile(r"&[a-zA-Z0-9#]+;")


def strip_html(text: str) -> str:
    text = _HTML_TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = _HTML_ENTITY_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_embedding_text(title: str, description: str = "") -> str:
    if not EMBEDDING_DESCRIPTION_CHARS or not description:
        return title
    clean_description = strip_html(description)
    if not clean_description:
        return title
    if EMBEDDING_DESCRIPTION_CHARS > 0:
        return f"{title}\n{clean_description[:EMBEDDING_DESCRIPTION_CHARS]}"
    return f"{title}\n{clean_description}"


# ── Model fingerprint ──────────────────────────────────────────────────────────

# Qdrant point ids must be uint64 or canonical UUIDs — arbitrary strings are
# rejected. Use a deterministic UUID so the sentinel is a valid, stable id.
_SENTINEL_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, "berga_model_sentinel"))
_PROBE_TEXT = "__berga_probe__"
_model_changed: bool = False
_current_fingerprint: str = ""


def compute_model_fingerprint(model) -> str:
    probe = model.encode(_PROBE_TEXT, normalize_embeddings=True, convert_to_numpy=True)
    probe_bytes = np.array(probe, dtype=np.float32).tobytes()
    raw = f"{MODEL_NAME}|{VECTOR_SIZE}|{hashlib.sha256(probe_bytes).hexdigest()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def is_model_changed() -> bool:
    return _model_changed


def get_current_fingerprint() -> str:
    return _current_fingerprint


def _check_model_fingerprint(client: QdrantClient, fingerprint: str) -> None:
    global _model_changed
    try:
        points = client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[_SENTINEL_ID],
            with_payload=True,
            with_vectors=False,
        )
        if points and points[0].payload:
            stored = points[0].payload.get("_model_fp")
            if stored and stored != fingerprint:
                _model_changed = True
                logger.critical(
                    "MODEL FINGERPRINT MISMATCH — stored=%s current=%s. "
                    "Re-embedding is required. Recommendations and similarity "
                    "search will produce wrong results until all vectors are "
                    "re-embedded with the new model.",
                    stored, fingerprint,
                )
                return
            elif stored == fingerprint:
                logger.info("Model fingerprint validated: %s", fingerprint)
                return
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[PointStruct(
                id=_SENTINEL_ID,
                vector=[0.0] * VECTOR_SIZE,
                payload={"_model_fp": fingerprint, "model_name": MODEL_NAME, "type": "sentinel"},
            )],
        )
        logger.info("Model fingerprint sentinel created: %s", fingerprint)
    except Exception:
        logger.warning("Could not check/set model fingerprint sentinel — continuing")


# ── Thread-safe singletons ─────────────────────────────────────────────────────

_model: Optional["_StaticEmbedder"] = None
_model_lock = threading.Lock()

_qdrant_client: Optional[QdrantClient] = None
_qdrant_lock = threading.Lock()


# ── Model loader ───────────────────────────────────────────────────────────────

def _locate_model_dir() -> Path:
    """
    Resolve the local snapshot directory for MODEL_NAME, mirroring the
    huggingface-hub cache layout. Uses local_files_only when
    HF_HUB_OFFLINE=1 so cached deployments never touch the network.
    """
    from huggingface_hub import snapshot_download

    home = os.environ.get("HF_HOME") or str(Path(os.environ.get("XDG_CACHE_HOME", "~/.cache")) / "huggingface")
    hub_dir = Path(home).expanduser() / "hub"

    fmt_kwargs = dict(repo_id=MODEL_NAME)
    if os.environ.get("HF_HOME"):
        fmt_kwargs["cache_dir"] = hub_dir
    if os.environ.get("HF_HUB_OFFLINE", "0") == "1":
        try:
            return Path(snapshot_download(local_files_only=True, **fmt_kwargs))
        except Exception as exc:
            # Cache miss (e.g. volume wiped with `docker compose down -v`).
            # Fail-soft: allow ONE online download instead of crash-looping
            # forever. Subsequent boots still use the offline cache.
            logger.warning(
                "HF_HUB_OFFLINE=1 but model '%s' is not cached under %s (%s) — "
                "attempting a one-time download to populate the cache",
                MODEL_NAME, hub_dir, exc,
            )
    return Path(snapshot_download(**fmt_kwargs))


def _load_safetensors_weights(path: Path) -> np.memmap:
    """
    Zero-copy load of the embedding table from a safetensors file.

    We bypass safetensors.numpy.load_file() because it materialises the
    entire file as anonymous RAM. A manual np.memmap over the tensor's
    byte range keeps the weights file-backed (shared + evictable).
    """
    with open(path, "rb") as f:
        (header_len,) = struct.unpack("<Q", f.read(8))
        header = json.loads(f.read(header_len))
    meta = header.get("embedding.weight")
    if meta is None:
        raise RuntimeError(f"{path} does not contain tensor 'embedding.weight'")
    dtype = _SAFETENSORS_DTYPE_MAP.get(meta["dtype"])
    if dtype is None:
        raise RuntimeError(
            f"Unsupported safetensors dtype '{meta['dtype']}' for numpy inference"
        )
    data_offset = 8 + header_len
    start, _end = meta["data_offsets"]
    return np.memmap(
        path, dtype=dtype, mode="r",
        offset=data_offset + start, shape=tuple(meta["shape"]),
    )


class _StaticEmbedder:
    """
    Minimal NumPy reimplementation of sentence-transformers'
    StaticEmbedding: tokenize (no special tokens) → mean of token
    embedding rows → truncate to VECTOR_SIZE (MRL) → L2-normalise.

    Exposes the same `.encode()` interface the rest of the codebase
    expects, so `affinity.py`, `parser.py` and `workers/tasks.py` need
    zero changes.
    """

    def __init__(self, model_dir: Path) -> None:
        weights_path = model_dir / _SAFETENSORS_RELPATH
        tokenizer_path = model_dir / _TOKENIZER_RELPATH
        if not weights_path.exists():
            raise RuntimeError(
                f"StaticEmbedding weights not found at {weights_path}. "
                "Only StaticEmbedding models are supported by the numpy backend."
            )
        if not tokenizer_path.exists():
            raise RuntimeError(
                f"Tokenizer file not found at {tokenizer_path}"
            )

        from tokenizers import Tokenizer
        self._weights = _load_safetensors_weights(weights_path)
        self._tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self.dim = int(self._weights.shape[1])

        logger.info(
            "Embedding model ready (backend=numpy-mmap, model=%s, table=%s, mrl_dim=%d)",
            MODEL_NAME, self._weights.shape, VECTOR_SIZE,
        )
        if VECTOR_SIZE > self.dim:
            raise ValueError(
                f"VECTOR_SIZE ({VECTOR_SIZE}) exceeds model dimension ({self.dim})"
            )

    def encode(
        self,
        sentences,
        *,
        batch_size: int = 64,  # accepted for interface parity — numpy has no batching knobs
        normalize_embeddings: bool = True,
        convert_to_numpy: bool = True,
        show_progress_bar: bool = False,  # noqa: ARG002
        **kwargs,  # noqa: ANN003
    ) -> np.ndarray:
        if not convert_to_numpy:
            raise ValueError("numpy backend only returns numpy arrays")
        single = isinstance(sentences, str)
        texts = [sentences] if single else list(sentences)

        out = np.empty((len(texts), VECTOR_SIZE), dtype=np.float32)
        for i, text in enumerate(texts):
            ids = self._tokenizer.encode(text, add_special_tokens=False).ids
            if ids:
                vec = np.asarray(self._weights[ids], dtype=np.float32).mean(axis=0)[:VECTOR_SIZE]
            else:
                vec = np.zeros(VECTOR_SIZE, dtype=np.float32)
            out[i] = vec

        if normalize_embeddings:
            norms = np.linalg.norm(out, axis=-1, keepdims=True)
            # Avoid division by zero for zero vectors
            norms = np.where(norms == 0, 1.0, norms)
            out = out / norms
        return out[0] if single else out


# ── Public accessors ───────────────────────────────────────────────────────────

def _load_model() -> "_StaticEmbedder":
    """Locate the cached model snapshot and build the numpy engine."""
    return _StaticEmbedder(_locate_model_dir())


def get_embedding_model() -> "_StaticEmbedder":
    """Return the shared embedding model instance (thread-safe, lazy)."""
    global _model, _current_fingerprint
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = _load_model()
                _current_fingerprint = compute_model_fingerprint(_model)
    return _model


def get_qdrant_client() -> QdrantClient:
    """Return the shared QdrantClient instance (thread-safe, lazy)."""
    global _qdrant_client
    if _qdrant_client is None:
        with _qdrant_lock:
            if _qdrant_client is None:
                host = os.environ.get("QDRANT_HOST", "localhost")
                port = int(os.environ.get("QDRANT_PORT", 6333))
                logger.info("Connecting to Qdrant at %s:%d", host, port)
                client = QdrantClient(
                    host=host,
                    port=port,
                    timeout=int(os.environ.get("QDRANT_TIMEOUT", "30")),
                )
                _ensure_collection(client)
                _qdrant_client = client
                logger.info("Qdrant client ready")
                get_embedding_model()
                if _current_fingerprint:
                    _check_model_fingerprint(client, _current_fingerprint)
                try:
                    info = client.get_collection(COLLECTION_NAME)
                    logger.info(
                        "Qdrant collection '%s': %d points, %d vectors",
                        COLLECTION_NAME, info.points_count, info.vectors_count,
                    )
                    if info.points_count > 300_000:
                        logger.warning(
                            "Qdrant has %d points — monitor memory usage carefully "
                            "(current limit: 384 MB)",
                            info.points_count,
                        )
                except Exception:
                    pass
    return _qdrant_client


# ── Collection management ──────────────────────────────────────────────────────

def _ensure_collection(client: QdrantClient) -> None:
    """Create the Qdrant collection if it doesn't exist, with scalar quantization."""
    try:
        existing = {c.name for c in client.get_collections().collections}

        if COLLECTION_NAME not in existing:
            logger.info("Creating Qdrant collection '%s'", COLLECTION_NAME)
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=DISTANCE_METRIC,
                    on_disk=True,
                ),
                quantization_config=ScalarQuantization(
                    scalar=ScalarQuantizationConfig(
                        type=ScalarType.INT8,
                        always_ram=False,
                    )
                ),
            )
            logger.info("Collection '%s' created (size=%d)", COLLECTION_NAME, VECTOR_SIZE)
        else:
            logger.debug("Collection '%s' already exists", COLLECTION_NAME)

        _ensure_payload_indices(client)

        if TAG_PHRASES_COLLECTION not in existing:
            logger.info("Creating Qdrant collection '%s'", TAG_PHRASES_COLLECTION)
            client.create_collection(
                collection_name=TAG_PHRASES_COLLECTION,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=DISTANCE_METRIC,
                    on_disk=True,
                ),
                quantization_config=ScalarQuantization(
                    scalar=ScalarQuantizationConfig(
                        type=ScalarType.INT8,
                        always_ram=False,
                    )
                ),
            )
            logger.info("Collection '%s' created (size=%d)", TAG_PHRASES_COLLECTION, VECTOR_SIZE)
        else:
            logger.debug("Collection '%s' already exists", TAG_PHRASES_COLLECTION)

    except Exception:
        logger.exception("Failed to ensure Qdrant collection/indices")
        raise


def _ensure_payload_indices(client: QdrantClient) -> None:
    """Create payload indices for efficient filtering. Idempotent."""
    indices = [
        ("pub_date", "datetime"),
        ("feed_sha256", "keyword"),
        ("url_hash", "keyword"),
        ("pub_timestamp", "float"),
        ("_model_fp", "keyword"),
    ]
    for field_name, field_schema in indices:
        try:
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field_name,
                field_schema=field_schema,
            )
            logger.debug("Payload index ensured: '%s' (%s)", field_name, field_schema)
        except UnexpectedResponse as exc:
            if "already exists" in str(exc).lower():
                logger.debug("Payload index '%s' already exists — skipping", field_name)
            else:
                logger.warning("Error creating payload index '%s': %s", field_name, exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unexpected error on payload index '%s': %s", field_name, exc)


# ── Embedding helpers ──────────────────────────────────────────────────────────

def embedding_text(text: str) -> list[float]:
    """
    Embed a single string and return a normalised float list.

    For bulk ingestion always prefer `embedding_batch()` — it is
    significantly faster due to batched matrix operations.
    """
    model = get_embedding_model()
    result = model.encode(
        text,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return np.array(result).tolist()


def embedding_batch(
    texts: list[str],
    batch_size: int = 64,
    show_progress: bool | None = None,
) -> list[list[float]]:
    """
    Embed multiple strings in batches. Use this for all RSS ingestion.

    Args:
        texts:          List of strings to embed.
        batch_size:     Number of strings per forward pass. 64 is a
                        good default for CPU; raise to 128+ with a GPU.
        show_progress:  Show a tqdm bar. Defaults to True when
                        len(texts) > 100, False otherwise.
    """
    if not texts:
        return []

    model = get_embedding_model()

    if show_progress is None:
        show_progress = len(texts) > 100

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=show_progress,
    )
    return np.array(embeddings).tolist()