"""
utils/profile_pack/pack_import.py — "bergapack" import of a user's
recommendation profile (counterpart of pack_export.py).

Compatibility policy:
  * affinity_boosts and the publisher engagement counters are
    model-independent — always imported.
  * affinity direction vectors are recomputed from the imported boost
    rows in the *target* instance's embedding model — valid regardless
    of the pack's origin model.
  * the learned pos/neg vectors are article embeddings — only applied
    when the pack's model fingerprint matches this instance's model.
    On a mismatch they are dropped and the profile re-learns gradually
    through future interactions (the existing learned vectors of the
    target account are kept untouched in that case).

Publisher counters are merged (max) instead of overwritten so that
re-importing the same pack or importing over existing local history
never double-counts or loses either side.
"""

import json
import logging
import math

from fastapi import HTTPException

from database.init_db import get_db
from intelligence.embeddings import (
    VECTOR_SIZE,
    get_embedding_model,
    get_current_fingerprint,
    compute_model_fingerprint,
)
from intelligence.affinity import _ensure_user_vector_row, _recompute_affinity_vector
from intelligence.recommendations import invalidate_cache

logger = logging.getLogger(__name__)

PACK_FORMAT = "bergapack"
PACK_VERSION = 1
_VALID_DIRECTIONS = ("positive", "negative")
_VECTOR_COLUMNS = ("pos_vector", "neg_vector")


def _current_model_fingerprint() -> str:
    fp = get_current_fingerprint()
    if fp:
        return fp
    return compute_model_fingerprint(get_embedding_model())


def _parse_pack(content: bytes) -> dict:
    try:
        pack = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    if not isinstance(pack, dict) or pack.get("format") != PACK_FORMAT:
        raise HTTPException(status_code=400, detail="Not a bergapack file")
    if pack.get("version") != PACK_VERSION:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported bergapack version: {pack.get('version')!r}",
        )
    if not isinstance(pack.get("vectors", {}), dict) or not isinstance(
        pack.get("affinity_boosts", []), list
    ):
        raise HTTPException(status_code=400, detail="Malformed bergapack structure")
    return pack


def _sanitise_vector(raw) -> list[float] | None:
    """Return a clean float vector of the right size, or None if unusable."""
    if not isinstance(raw, list) or len(raw) != VECTOR_SIZE:
        return None
    try:
        values = [float(v) for v in raw]
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(v) for v in values):
        return None
    return values


def _sanitise_boosts(raw_boosts) -> list[dict]:
    """Keep only well-formed boost rows with a positive strength in [0, 1]."""
    clean = []
    seen = set()
    for raw in raw_boosts:
        if not isinstance(raw, dict):
            continue
        term = (raw.get("term") or "").strip()
        direction = raw.get("direction")
        try:
            strength = float(raw.get("strength", 0.0))
        except (TypeError, ValueError):
            continue
        key = (term.lower(), direction)
        if not term or direction not in _VALID_DIRECTIONS or key in seen:
            continue
        if not 0.0 < strength <= 1.0:
            continue
        seen.add(key)
        clean.append({"term": term, "direction": direction, "strength": strength})
    return clean


def _merge_counter_map(existing_raw: str | None, imported: dict) -> str:
    """Merge two {'<feed_sha>': count} maps keeping the larger count per key."""
    try:
        existing = json.loads(existing_raw) if existing_raw else {}
        if not isinstance(existing, dict):
            existing = {}
    except (json.JSONDecodeError, ValueError):
        existing = {}
    for key, value in imported.items():
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        existing[key] = max(float(existing.get(key, 0.0)), value)
    return json.dumps(existing)


def _apply_affinity_vectors(cursor, user_id: int) -> None:
    """Rebuild both affinity direction vectors from the boost history in-transaction."""
    for direction, column in (
        ("positive", "affinity_pos_vector"),
        ("negative", "affinity_neg_vector"),
    ):
        vec = _recompute_affinity_vector(user_id, direction, cursor=cursor)
        cursor.execute(
            f"UPDATE user_vectors SET {column} = %s WHERE user_id = %s",
            (
                json.dumps(vec.astype("float32").tolist()) if vec is not None else None,
                user_id,
            ),
        )


def receive(content: bytes, user: dict) -> dict:
    pack = _parse_pack(content)
    user_id = user["id"]

    pack_model = pack.get("model") or {}
    pack_vectors = pack.get("vectors") or {}
    boosts = _sanitise_boosts(pack.get("affinity_boosts") or [])

    current_fp = _current_model_fingerprint()
    model_compatible = (
        pack_model.get("fingerprint") == current_fp
        and pack_model.get("vector_size") == VECTOR_SIZE
    )

    learned_vectors: dict[str, list[float]] = {}
    if model_compatible:
        for column in _VECTOR_COLUMNS:
            vec = _sanitise_vector(pack_vectors.get(column))
            if vec is not None:
                learned_vectors[column] = vec

    imported_pub_likes = pack_vectors.get("publisher_likes") or {}
    imported_pub_dislikes = pack_vectors.get("publisher_dislikes") or {}
    if not isinstance(imported_pub_likes, dict):
        imported_pub_likes = {}
    if not isinstance(imported_pub_dislikes, dict):
        imported_pub_dislikes = {}

    vectors_applied = False
    boosts_applied = 0

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            _ensure_user_vector_row(user_id, cursor)

            if learned_vectors:
                set_parts, params = [], []
                for column in _VECTOR_COLUMNS:
                    if column not in learned_vectors:
                        continue
                    set_parts.append(f"{column} = %s")
                    params.append(json.dumps(learned_vectors[column]))
                params.append(user_id)
                cursor.execute(
                    f"UPDATE user_vectors SET {', '.join(set_parts)} WHERE user_id = %s",
                    tuple(params),
                )
                vectors_applied = True

            if imported_pub_likes or imported_pub_dislikes:
                cursor.execute(
                    "SELECT publisher_likes, publisher_dislikes "
                    "FROM user_vectors WHERE user_id = %s",
                    (user_id,),
                )
                row = cursor.fetchone()
                cursor.execute(
                    """
                    UPDATE user_vectors
                    SET publisher_likes = %s, publisher_dislikes = %s
                    WHERE user_id = %s
                    """,
                    (
                        _merge_counter_map(row.get("publisher_likes") if row else None, imported_pub_likes),
                        _merge_counter_map(row.get("publisher_dislikes") if row else None, imported_pub_dislikes),
                        user_id,
                    ),
                )

            for boost in boosts:
                cursor.execute(
                    """
                    INSERT INTO affinity_boosts (user_id, term, direction, strength)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE strength = GREATEST(strength, VALUES(strength))
                    """,
                    (user_id, boost["term"], boost["direction"], boost["strength"]),
                )
                boosts_applied += 1

            if boosts:
                _apply_affinity_vectors(cursor, user_id)

            conn.commit()
        except HTTPException:
            conn.rollback()
            raise
        except Exception as e:
            conn.rollback()
            logger.exception("Profile pack import failed user=%s", user_id)
            raise HTTPException(status_code=500, detail=f"Import failed: {e}")
        finally:
            cursor.close()

    invalidate_cache(user_id)

    status = "imported" if (vectors_applied or boosts_applied) else "empty"
    reason = None
    if not model_compatible and pack_vectors.get("pos_vector"):
        status = "partial"
        reason = "model_mismatch"

    logger.info(
        "Profile pack imported: user=%s status=%s vectors=%s boosts=%s "
        "pub_likes=%s pub_dislikes=%s pack_model=%r",
        user_id, status, vectors_applied, boosts_applied,
        len(imported_pub_likes), len(imported_pub_dislikes), pack_model.get("name"),
    )

    return {
        "status": status,
        "reason": reason,
        "vectors": vectors_applied,
        "boosts": boosts_applied,
        "publisher_likes": len(imported_pub_likes),
        "publisher_dislikes": len(imported_pub_dislikes),
    }
