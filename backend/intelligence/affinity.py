"""
intelligence/affinity.py — Affinity analysis and manual vector tuning.

Affinity boosts are stored in SEPARATE columns (affinity_pos_vector /
affinity_neg_vector) so manual boosts NEVER corrupt the interaction-
learned pos_vector / neg_vector.  The recommendation engine blends
both at query time via AFFINITY_WEIGHT.

Boost history is tracked in the affinity_boosts table for reversibility.
"""

from __future__ import annotations

import json
import logging
import math

import numpy as np

from database.init_db import get_db
from intelligence.embeddings import get_embedding_model
from intelligence.scoring_util import (
    cosine_similarity,
    contrast_score,
    ema_blend_and_normalise,
    blend_vectors,
)
from intelligence.recommendations import invalidate_cache

logger = logging.getLogger(__name__)

_EPS = 1e-6
_DEFAULT_STRENGTH = 0.25
_MIN_STRENGTH = 0.05
_MAX_STRENGTH = 0.90


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_user_rows(user_id: int) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """SELECT pos_vector, neg_vector,
                          affinity_pos_vector, affinity_neg_vector
                   FROM user_vectors WHERE user_id = %s""",
                (user_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()


def _embed_term(term: str) -> np.ndarray:
    """
    Encode a single term into a 1-D float32 vector.
    .ravel() guarantees shape (dim,) even when the model
    returns (1, dim) for a single string.
    """
    vec = get_embedding_model().encode(
        term,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return np.asarray(vec, dtype=np.float32).ravel()


def _ensure_user_vector_row(user_id: int, cursor) -> None:
    """
    Guarantee a row exists in user_vectors for this user.
    Uses INSERT … ON DUPLICATE KEY UPDATE so it's a no-op when
    the row already exists.

    IMPORTANT: pos_vector is defined as LONGTEXT NOT NULL in the schema
    (see init_db.py), so we MUST provide a value on INSERT.  An empty
    JSON array '[]' is used as a placeholder — it will be replaced with
    a real embedding once the user interacts with articles.
    _safe_json_loads_vector treats '[]' as None, and the recommendation
    engine skips users with no real pos_vector, so this is safe.
    """
    cursor.execute(
        """
        INSERT INTO user_vectors (
            user_id,
            pos_vector,
            neg_vector,
            affinity_pos_vector,
            affinity_neg_vector,
            publisher_likes,
            publisher_dislikes,
            publisher_freq
        )
        VALUES (%s, '[]', NULL, NULL, NULL, '{}', '{}', '{}')
        ON DUPLICATE KEY UPDATE user_id = user_id
        """,
        (user_id,),
    )


def _safe_json_loads_vector(raw: str | None) -> np.ndarray | None:
    """
    Parse a JSON-encoded vector from the database, returning None for
    NULL / empty-string / empty-array / malformed data instead of raising.
    Also rejects vectors containing NaN or Inf.
    """
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if not parsed:
            return None
        arr = np.array(parsed, dtype=np.float32)
        if not np.all(np.isfinite(arr)):
            logger.warning("Vector contains NaN/Inf — treating as absent")
            return None
        return arr
    except (json.JSONDecodeError, ValueError):
        logger.warning("Could not decode vector from DB — treating as absent")
        return None


def _safe_vector_for_json(vec: np.ndarray) -> str:
    """
    Serialise a vector to JSON, replacing any NaN / Inf with 0 so the
    output is always valid JSON.  json.dumps(float('nan')) produces
    'NaN' which is not valid JSON and crashes the browser's JSON.parse().
    """
    cleaned = np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)
    return json.dumps(cleaned.tolist())


def _recompute_affinity_vector(user_id: int, direction: str) -> np.ndarray | None:
    """
    Recompute an affinity vector from scratch using the boost history.
    This allows accurate removal of individual boosts.
    """
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT term, strength FROM affinity_boosts
                WHERE user_id = %s AND direction = %s
                ORDER BY created_at ASC
                """,
                (user_id, direction),
            )
            boosts = cursor.fetchall()
        finally:
            cursor.close()

    if not boosts:
        return None

    result: np.ndarray | None = None
    for boost in boosts:
        term_vec = _embed_term(boost["term"])
        strength = float(boost["strength"])
        result = ema_blend_and_normalise(result, term_vec, strength)

    return result


# ── Public service functions ───────────────────────────────────────────────────

def analyze_affinity(user_id: int, term: str) -> dict:
    """
    Return the affinity score for a term against the user's COMBINED profile
    (learned interactions + manual affinity boosts), mirroring what the
    recommendation engine sees.
    """
    row = _get_user_rows(user_id)
    if not row:
        return {"affinity": 0.5, "sim_pos": 0.0, "sim_neg": 0.0, "term": term}

    try:
        from intelligence.recommendations import AFFINITY_WEIGHT

        term_vec = _embed_term(term)

        # ── Decode all four vectors (any may be None) ────────────────────
        pos_vec = _safe_json_loads_vector(row.get("pos_vector"))
        aff_pos = _safe_json_loads_vector(row.get("affinity_pos_vector"))
        neg_vec = _safe_json_loads_vector(row.get("neg_vector"))
        aff_neg = _safe_json_loads_vector(row.get("affinity_neg_vector"))

        # ── Effective positive vector ────────────────────────────────────
        if pos_vec is not None and aff_pos is not None:
            effective_pos = np.array(
                blend_vectors(pos_vec.tolist(), aff_pos.tolist(), AFFINITY_WEIGHT),
                dtype=np.float32,
            )
        elif pos_vec is not None:
            effective_pos = pos_vec
        elif aff_pos is not None:
            effective_pos = aff_pos
        else:
            return {"affinity": 0.5, "sim_pos": 0.0, "sim_neg": 0.0, "term": term}

        sim_pos = float(cosine_similarity(term_vec, effective_pos))

        # An explicit affinity boost should always be visible in the
        # analysis.  If the pure affinity vector produces a higher similarity
        # than the blended one, use that.
        if aff_pos is not None:
            sim_pos = max(sim_pos, float(cosine_similarity(term_vec, aff_pos)))

        # ── Effective negative vector ────────────────────────────────────
        if neg_vec is not None and aff_neg is not None:
            effective_neg = np.array(
                blend_vectors(neg_vec.tolist(), aff_neg.tolist(), AFFINITY_WEIGHT),
                dtype=np.float32,
            )
            sim_neg = float(cosine_similarity(term_vec, effective_neg))
        elif neg_vec is not None:
            sim_neg = float(cosine_similarity(term_vec, neg_vec))
        elif aff_neg is not None:
            sim_neg = float(cosine_similarity(term_vec, aff_neg))
        else:
            sim_neg = 0.0

        if aff_neg is not None:
            sim_neg = max(sim_neg, float(cosine_similarity(term_vec, aff_neg)))

        # ── Clamp similarity values to a sane range ──────────────────────
        # Blended / un-normalised vectors can produce values slightly
        # outside [-1, 1] or even NaN.  Clamp so contrast_score stays in
        # [0, 1] and the JSON response is always valid.
        sim_pos = 0.0 if (math.isnan(sim_pos) or math.isinf(sim_pos)) else max(0.0, min(1.0, sim_pos))
        sim_neg = 0.0 if (math.isnan(sim_neg) or math.isinf(sim_neg)) else max(0.0, min(1.0, sim_neg))

        affinity = contrast_score(sim_pos, sim_neg)

        # Final safety clamp
        if math.isnan(affinity) or math.isinf(affinity):
            affinity = 0.5
        affinity = max(0.0, min(1.0, affinity))

    except Exception:
        logger.exception("Error computing affinity term=%r user=%s", term, user_id)
        raise

    return {
        "affinity": round(float(affinity), 4),
        "sim_pos": round(float(sim_pos), 4),
        "sim_neg": round(float(sim_neg), 4),
        "term": term,
    }


def boost_affinity(user_id: int, term: str, direction: str, strength: float) -> dict:
    """Nudge affinity_pos_vector or affinity_neg_vector. Records in boost history."""
    strength = max(_MIN_STRENGTH, min(strength, _MAX_STRENGTH))

    try:
        term_vec = _embed_term(term)

        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                # Ensure the row exists before reading / writing.
                _ensure_user_vector_row(user_id, cursor)

                # Read the current vectors on the SAME connection so we
                # always see the latest data.
                cursor.execute(
                    """SELECT affinity_pos_vector, affinity_neg_vector
                       FROM user_vectors WHERE user_id = %s""",
                    (user_id,),
                )
                row = cursor.fetchone()

                # Record the boost in history
                cursor.execute(
                    """
                    INSERT INTO affinity_boosts (user_id, term, direction, strength)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (user_id, term, direction, strength),
                )

                # Apply the EMA blend
                if direction == "positive":
                    existing = _safe_json_loads_vector(
                        row["affinity_pos_vector"] if row else None
                    )
                    new_vec = ema_blend_and_normalise(existing, term_vec, strength)
                    cursor.execute(
                        "UPDATE user_vectors SET affinity_pos_vector = %s WHERE user_id = %s",
                        (_safe_vector_for_json(new_vec), user_id),
                    )
                else:
                    existing = _safe_json_loads_vector(
                        row["affinity_neg_vector"] if row else None
                    )
                    new_vec = ema_blend_and_normalise(existing, term_vec, strength)
                    cursor.execute(
                        "UPDATE user_vectors SET affinity_neg_vector = %s WHERE user_id = %s",
                        (_safe_vector_for_json(new_vec), user_id),
                    )

                conn.commit()
            finally:
                cursor.close()

    except Exception:
        logger.exception(
            "Error applying boost term=%r direction=%s user=%s",
            term, direction, user_id,
        )
        raise

    invalidate_cache(user_id)
    logger.info(
        "Affinity boost: user=%s term=%r direction=%s strength=%.2f",
        user_id, term, direction, strength,
    )
    return {"success": True, "direction": direction, "term": term, "strength": strength}


def remove_affinity_boost(user_id: int, term: str, direction: str) -> dict:
    """Remove a specific boost and recompute the affinity vector from remaining history."""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                DELETE FROM affinity_boosts
                WHERE user_id = %s AND term = %s AND direction = %s
                LIMIT 1
                """,
                (user_id, term, direction),
            )
            deleted = cursor.rowcount > 0

            if not deleted:
                return {"success": False, "message": "Boost not found"}

            _ensure_user_vector_row(user_id, cursor)

            new_vec = _recompute_affinity_vector(user_id, direction)

            column = "affinity_pos_vector" if direction == "positive" else "affinity_neg_vector"
            cursor.execute(
                f"UPDATE user_vectors SET {column} = %s WHERE user_id = %s",
                (_safe_vector_for_json(new_vec) if new_vec is not None else None, user_id),
            )

            conn.commit()
        finally:
            cursor.close()

    invalidate_cache(user_id)
    logger.info(
        "Affinity boost removed: user=%s term=%r direction=%s",
        user_id, term, direction,
    )
    return {"success": True, "direction": direction, "term": term}