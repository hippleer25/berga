"""
intelligence/embeddings.py — Embedding model and Qdrant client singletons.

Thread-safe initialisation with double-checked locking.

Runtime backend: ONNX int8 (model_int8.onnx)
  – Eliminates the PyTorch runtime (~400–800 MB saved).
  – Model weights shrink from ~434 MB (fp32) to ~108 MB (int8).
  – Quality loss vs fp32 is statistically negligible for STS tasks.

If the ONNX file is unavailable (e.g. the model repo doesn't ship it),
the loader falls back to the plain ONNX fp32 backend, logging a warning.
"""

from __future__ import annotations

import html
import hashlib
import logging
import os
import re
import threading
import uuid
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer
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

# ONNX file preference order — first available wins.
# model_int8.onnx  →  108 MB, negligible quality loss for STS tasks (recommended)
# model_fp16.onnx  →  217 MB, half of fp32, lossless
# model.onnx       →  434 MB, fp32 baseline (no RAM gain vs PyTorch)
_ONNX_CANDIDATES = (
    "onnx/model_int8.onnx",
    "onnx/model_fp16.onnx",
    "onnx/model.onnx",
)

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

_model: Optional[SentenceTransformer] = None
_model_lock = threading.Lock()

_qdrant_client: Optional[QdrantClient] = None
_qdrant_lock = threading.Lock()


# ── Model loader ───────────────────────────────────────────────────────────────

def _load_model() -> SentenceTransformer:
    """
    Load the SentenceTransformer with the best available ONNX variant.

    Strategy:
      1. Try each candidate ONNX file in order (int8 → fp16 → fp32).
      2. After loading, verify that truncate_dim is respected by running
         a one-sentence probe. If the output dimension doesn't match
         VECTOR_SIZE, the backend silently ignored truncate_dim — in that
         case we apply manual post-encode truncation via a wrapper.
      3. If no ONNX backend works at all, raise so the operator knows
         immediately rather than silently running fp32 PyTorch.
    """
    last_exc: Optional[Exception] = None

    for onnx_file in _ONNX_CANDIDATES:
        try:
            logger.info(
                "Loading embedding model '%s' via ONNX backend (file=%s, truncate_dim=%d)",
                MODEL_NAME,
                onnx_file,
                VECTOR_SIZE,
            )
            model = SentenceTransformer(
                MODEL_NAME,
                backend="onnx",
                model_kwargs={"file_name": onnx_file},
            truncate_dim=VECTOR_SIZE,
        )
            # ── Sanity check: does truncate_dim actually work? ─────────────
            probe = model.encode("probe", convert_to_numpy=True)
            actual_dim = int(np.array(probe).shape[-1])

            if actual_dim != VECTOR_SIZE:
                logger.warning(
                    "ONNX backend ignored truncate_dim=%d (got dim=%d). "
                    "Manual truncation will be applied at encode time.",
                    VECTOR_SIZE,
                    actual_dim,
                )
                return _TruncatingModel(model, VECTOR_SIZE)

            logger.info(
                "Embedding model ready (backend=onnx, file=%s, dim=%d)",
                onnx_file,
                actual_dim,
            )
            return model

        except Exception as exc: # noqa: BLE001
            logger.warning(
            "Could not load ONNX file '%s': %s — trying next candidate.",
            onnx_file,
            exc,
        )
        last_exc = exc

    raise RuntimeError(
        f"No ONNX variant could be loaded for model '{MODEL_NAME}'. "
        f"Tried: {_ONNX_CANDIDATES}. Last error: {last_exc}"
    )


class _TruncatingModel:
    """
    Thin wrapper that truncates embeddings post-encode when the ONNX backend
    ignores `truncate_dim`. Exposes the same `.encode()` interface as
    SentenceTransformer so the rest of the codebase needs zero changes.
    """

    def __init__(self, inner: SentenceTransformer, dim: int) -> None:
        self._inner = inner
        self._dim = dim

    def encode(
        self,
        sentences,
        *,
        batch_size: int = 64,
        normalize_embeddings: bool = True,
        convert_to_numpy: bool = True,
        show_progress_bar: bool = False,
        **kwargs,
    ) -> np.ndarray:
        embeddings = self._inner.encode(
            sentences,
            batch_size=batch_size,
            normalize_embeddings=False,   # normalise *after* truncation
            convert_to_numpy=True,
            show_progress_bar=show_progress_bar,
            **kwargs,
        )
        embeddings = np.array(embeddings)[..., : self._dim]

        if normalize_embeddings:
            norms = np.linalg.norm(embeddings, axis=-1, keepdims=True)
            # Avoid division by zero for zero vectors
            norms = np.where(norms == 0, 1.0, norms)
            embeddings = embeddings / norms

        return embeddings


# ── Public accessors ───────────────────────────────────────────────────────────

def get_embedding_model() -> SentenceTransformer | _TruncatingModel:
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