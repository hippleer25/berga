"""
intelligence/affinity.py — Affinity analysis and manual vector tuning.

Affinity boosts are stored in SEPARATE columns (affinity_pos_vector /
affinity_neg_vector) so manual boosts NEVER corrupt the interaction-
learned pos_vector / neg_vector.  The recommendation engine blends
both at query time via AFFINITY_WEIGHT.

Boost model: each term+direction carries a RELATIVE weight in [0, 1]
(one row per term in affinity_boosts). Each UI click adds/removes
AFFINITY_CLICK_STEP; the direction vector is the normalised weighted
mean of the boosted term vectors.

Displayed affinity scores are a calibrated logistic remap of the raw
contrast (see calibrated_affinity) so typical interests don't all read
"very low"; ranking always uses the raw, unbounded contrast.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os

import numpy as np

from database.init_db import get_db
from intelligence.embeddings import get_embedding_model
from intelligence.scoring_util import (
    calibrated_affinity,
    cosine_similarity,
    contrast_score,
    blend_vectors,
)
from intelligence.recommendations import invalidate_cache

logger = logging.getLogger(__name__)

_EPS = 1e-6

# ── Calibration of the displayed affinity score ───────────────────────────────
# The displayed affinity is a logistic remap of the raw contrast score:
#     display = σ((contrast − mu) / tau)
# The raw contrast (unbounded) stays the ranking / engine signal; only the
# presentation is calibrated so typical interests don't all read "very low".
AFFINITY_CAL_MU = float(os.getenv("AFFINITY_CAL_MU", "0.15"))
AFFINITY_CAL_TAU = float(os.getenv("AFFINITY_CAL_TAU", "0.12"))

# Manual boosts: relative per-term weight in [0, 1]. Each UI click adds or
# removes AFFINITY_CLICK_STEP of weight for that term+direction.
AFFINITY_CLICK_STEP = 0.10


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


def _embed_term(term: str | list[str]) -> np.ndarray | np.ndarray:
    """
    Encode one term (→ shape (dim,)) or a list of terms (→ (n, dim)) into
    float32 vector(s).
    """
    vec = get_embedding_model().encode(
        term,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return np.asarray(vec, dtype=np.float32)


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


def _effective_profile_vectors(row: dict) -> tuple[np.ndarray | None, np.ndarray | None]:
    """
    Build the effective (eff_pos, eff_neg) profile pair for a user_vectors
    row, blending interaction-learned vectors with manual affinity vectors
    via AFFINITY_WEIGHT. Either side may be None. Mirrors what the
    recommendation engine queries with, so all analyses agree with it.
    """
    from intelligence.recommendations import AFFINITY_WEIGHT

    pos_vec = _safe_json_loads_vector(row.get("pos_vector"))
    aff_pos = _safe_json_loads_vector(row.get("affinity_pos_vector"))
    neg_vec = _safe_json_loads_vector(row.get("neg_vector"))
    aff_neg = _safe_json_loads_vector(row.get("affinity_neg_vector"))

    if pos_vec is not None and aff_pos is not None:
        eff_pos = np.array(
            blend_vectors(pos_vec.tolist(), aff_pos.tolist(), AFFINITY_WEIGHT),
            dtype=np.float32,
        )
    else:
        eff_pos = pos_vec if pos_vec is not None else aff_pos

    if neg_vec is not None and aff_neg is not None:
        eff_neg = np.array(
            blend_vectors(neg_vec.tolist(), aff_neg.tolist(), AFFINITY_WEIGHT),
            dtype=np.float32,
        )
    else:
        eff_neg = neg_vec if neg_vec is not None else aff_neg

    return eff_pos, eff_neg


def _sanitise_similarity(value: float) -> float:
    """Clamp a cosine similarity to [0, 1], mapping NaN/Inf to 0."""
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return max(0.0, min(1.0, value))


def _recompute_affinity_vector(
    user_id: int,
    direction: str,
    cursor=None,
) -> np.ndarray | None:
    """
    Recompute an affinity vector from the boost history.

    Model: a weighted mean of the boosted term vectors, normalised —
        vec = Σ wᵢ · term_vecᵢ / ‖Σ wᵢ · term_vecᵢ‖
    where wᵢ ∈ [0, 1] is each term's relative weight (one row per
    term+direction, maintained by the ±step upsert in boost_affinity()).

    When ``cursor`` is given, the boost rows are read through the caller's
    open transaction so uncommitted deletes/updates are visible; a stale
    read from a second connection would resurrect just-removed boosts.
    Returns None when there are no boosts left.
    """
    if cursor is not None:
        cursor.execute(
            "SELECT term, strength FROM affinity_boosts "
            "WHERE user_id = %s AND direction = %s",
            (user_id, direction),
        )
        boosts = cursor.fetchall()
    else:
        with get_db() as conn:
            db_cursor = conn.cursor(dictionary=True)
            try:
                db_cursor.execute(
                    "SELECT term, strength FROM affinity_boosts "
                    "WHERE user_id = %s AND direction = %s",
                    (user_id, direction),
                )
                boosts = db_cursor.fetchall()
            finally:
                db_cursor.close()

    if not boosts:
        return None

    # Term vectors come from the shared batched cache helper — a click must
    # never pay one embedding encode per boost row.
    term_vecs = _get_term_vectors([b["term"] for b in boosts])
    missing = [b["term"] for b in boosts if b["term"] not in term_vecs]
    if missing:
        # Fail loud (parity with the previous per-term encode): a partial
        # recomputation would silently drift the user's profile.
        raise RuntimeError(f"Could not embed boost terms: {missing!r}")

    result: np.ndarray | None = None
    for boost in boosts:
        contribution = float(boost["strength"]) * term_vecs[boost["term"]]
        result = contribution if result is None else result + contribution

    if result is None:
        return None
    norm = np.linalg.norm(result)
    if norm <= 0:
        return None
    return (result / norm).astype(np.float32)


# ── Public service functions ───────────────────────────────────────────────────

def analyze_affinity(user_id: int, term: str) -> dict:
    """
    Return the affinity score for a term against the user's COMBINED profile
    (learned interactions + manual affinity boosts), mirroring what the
    recommendation engine sees.

    The displayed ``affinity`` is the calibrated (logistic) remap of the raw
    contrast score, so a typical interest reads mid-range even for users
    with thin profiles. ``sim_pos`` / ``sim_neg`` stay raw for transparency.
    The current manual boost weight per direction is included so the UI can
    render ± steppers.
    """
    row = _get_user_rows(user_id)
    if not row:
        return {
            "affinity": 0.5,
            "sim_pos": 0.0,
            "sim_neg": 0.0,
            "boost_pos": 0.0,
            "boost_neg": 0.0,
            "term": term,
        }

    try:
        term_vec = _embed_term(term)

        eff_pos, eff_neg = _effective_profile_vectors(row)
        if eff_pos is None:
            return {
                "affinity": 0.5,
                "sim_pos": 0.0,
                "sim_neg": 0.0,
                "boost_pos": 0.0,
                "boost_neg": 0.0,
                "term": term,
            }

        sim_pos = float(cosine_similarity(term_vec, eff_pos))

        if eff_neg is not None:
            sim_neg = float(cosine_similarity(term_vec, eff_neg))
        else:
            sim_neg = 0.0

        sim_pos = _sanitise_similarity(sim_pos)
        sim_neg = _sanitise_similarity(sim_neg)

        raw_contrast = contrast_score(sim_pos, sim_neg)
        if math.isnan(raw_contrast) or math.isinf(raw_contrast):
            raw_contrast = 0.0
        affinity = calibrated_affinity(raw_contrast, AFFINITY_CAL_MU, AFFINITY_CAL_TAU)

        boost_pos, boost_neg = _get_boost_weights(user_id, term)

    except Exception:
        logger.exception("Error computing affinity term=%r user=%s", term, user_id)
        raise

    return {
        "affinity": round(float(affinity), 4),
        "sim_pos": round(float(sim_pos), 4),
        "sim_neg": round(float(sim_neg), 4),
        "boost_pos": round(float(boost_pos), 4),
        "boost_neg": round(float(boost_neg), 4),
        "term": term,
    }


def _get_boost_weights(user_id: int, term: str) -> tuple[float, float]:
    """Current manual boost weight for a term, per direction."""
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT direction, strength FROM affinity_boosts "
                "WHERE user_id = %s AND term = %s",
                (user_id, term),
            )
            rows = cursor.fetchall()
        finally:
            cursor.close()

    weights = {r["direction"]: float(r["strength"]) for r in rows}
    return weights.get("positive", 0.0), weights.get("negative", 0.0)


def boost_affinity(user_id: int, term: str, direction: str, strength: float) -> dict:
    """
    Adjust the relative boost weight of a term by a signed delta.

    ``strength`` is the click delta (e.g. +0.10 / −0.10). The per-term
    relative weight lives in [0, 1]; a single row per (user, term,
    direction) is kept up to date. Dropping to 0 removes the boost
    entirely and recomputes the direction vector (possibly back to None).
    """
    delta = max(-1.0, min(1.0, float(strength)))
    if delta == 0.0:
        return {"success": False, "message": "Empty adjustment"}

    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                # Ensure the row exists before reading / writing.
                _ensure_user_vector_row(user_id, cursor)

                # Atomic relative-weight step. The UNIQUE key (user_id, term,
                # direction) makes concurrent clicks merge into a single row
                # inside the DB instead of racing SELECT-then-INSERT duplicates.
                # A fresh insert of a negative delta lands at strength 0 and is
                # cleaned up right after (weight 0 ⇒ boost deleted).
                insert_value = max(0.0, min(1.0, delta))
                cursor.execute(
                    """
                    INSERT INTO affinity_boosts (user_id, term, direction, strength)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        strength = LEAST(1.0, GREATEST(0.0, strength + %s))
                    """,
                    (user_id, term, direction, insert_value, delta),
                )

                # Read the final weight through this same transaction so the
                # row lock taken by the upsert is still held (no race window).
                cursor.execute(
                    "SELECT strength FROM affinity_boosts "
                    "WHERE user_id = %s AND term = %s AND direction = %s "
                    "LIMIT 1",
                    (user_id, term, direction),
                )
                final_row = cursor.fetchone()
                new_weight = float(final_row["strength"]) if final_row else 0.0

                if new_weight <= 0.0:
                    cursor.execute(
                        "DELETE FROM affinity_boosts "
                        "WHERE user_id = %s AND term = %s AND direction = %s",
                        (user_id, term, direction),
                    )

                new_vec = _recompute_affinity_vector(user_id, direction, cursor=cursor)

                column = (
                    "affinity_pos_vector" if direction == "positive" else "affinity_neg_vector"
                )
                cursor.execute(
                    f"UPDATE user_vectors SET {column} = %s WHERE user_id = %s",
                    (_safe_vector_for_json(new_vec) if new_vec is not None else None, user_id),
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
        "Affinity boost: user=%s term=%r direction=%s delta=%+.2f weight=%.2f",
        user_id, term, direction, delta, new_weight,
    )
    return {
        "success": True,
        "direction": direction,
        "term": term,
        "weight": round(new_weight, 4),
    }


def remove_affinity_boost(user_id: int, term: str, direction: str) -> dict:
    """Remove a specific boost and recompute the affinity vector from remaining history."""
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                DELETE FROM affinity_boosts
                WHERE user_id = %s AND term = %s AND direction = %s
                """,
                (user_id, term, direction),
            )
            deleted = cursor.rowcount > 0

            if not deleted:
                return {"success": False, "message": "Boost not found"}

            _ensure_user_vector_row(user_id, cursor)

            new_vec = _recompute_affinity_vector(user_id, direction, cursor=cursor)

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


def reset_user_affinity(user_id: int) -> dict:
    """
    Revert every manual boost for a user in one shot: all affinity_boosts
    rows are deleted and both affinity direction vectors are re-NULLed, so
    the interaction-learned profile alone drives recommendations again.
    The learned profile itself is untouched. Returns the number of boosts
    removed (0 is a valid result — a clean no-op reset).
    """
    removed = 0
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(
                    "DELETE FROM affinity_boosts WHERE user_id = %s",
                    (user_id,),
                )
                removed = cursor.rowcount

                cursor.execute(
                    "UPDATE user_vectors SET "
                    "affinity_pos_vector = NULL, affinity_neg_vector = NULL "
                    "WHERE user_id = %s",
                    (user_id,),
                )
                conn.commit()
            finally:
                cursor.close()
    except Exception:
        logger.exception("Error resetting affinity boosts user=%s", user_id)
        raise

    invalidate_cache(user_id)
    logger.info("Affinity reset: user=%s removed=%s", user_id, removed)
    return {"success": True, "removed_boosts": removed}

# ── Cluster affinity attachment (weekly events enrichment) ────────────────────

def attach_cluster_affinity(user_id: int, events: list[dict]) -> list[dict]:
    """
    Annotate each weekly event with an ``affinity_pct`` score (0–100) — how
    much the cluster's articles match the user's reading profile.

    Mirrors analyze_affinity()'s effective-vector blending, but scores whole
    clusters: one Qdrant batch retrieve grabs the stored vectors of every
    cluster member (they were indexed at ingest), then a mean-cosine contrast
    against the user's effective pos/neg profile yields a raw score per
    event. The scores are converted to a relative in-request percentile so
    the UI can show "how much more this cluster is for you than the others"
    without any global calibration.

    Users without vectors are returned untouched — the frontend hides the
    chip when the field is absent. Failures never break the events payload.
    """
    if not events:
        return events

    try:
        row = _get_user_rows(user_id)
        if not row:
            return events

        from intelligence.embeddings import get_qdrant_client, COLLECTION_NAME

        eff_pos, eff_neg = _effective_profile_vectors(row)
        eff_pos = eff_pos.astype(np.float64) if eff_pos is not None else None
        eff_neg = eff_neg.astype(np.float64) if eff_neg is not None else None

        if eff_pos is None:
            return events

        # Collect unique article ids across all events — one Qdrant call.
        ids: list[str] = []
        seen: set[str] = set()
        for event in events:
            for article in event.get("articles", []):
                item_id = article.get("item_id")
                if item_id and item_id not in seen:
                    seen.add(item_id)
                    ids.append(item_id)
        if not ids:
            return events

        client = get_qdrant_client()
        points = client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=ids,
            with_payload=False,
            with_vectors=True,
        )
        vec_map = {str(p.id): np.asarray(p.vector, dtype=np.float64) for p in points}
        if not vec_map:
            return events

        raw_scores: list[float] = []
        for event in events:
            sims_pos: list[float] = []
            sims_neg: list[float] = []
            for article in event.get("articles", []):
                vec = vec_map.get(str(article.get("item_id") or ""))
                if vec is None:
                    continue
                sims_pos.append(cosine_similarity(vec, eff_pos))
                if eff_neg is not None:
                    sims_neg.append(cosine_similarity(vec, eff_neg))
            if not sims_pos:
                raw_scores.append(float("nan"))
                continue
            sim_pos = float(np.mean(sims_pos))
            sim_neg = float(np.mean(sims_neg)) if sims_neg else 0.0
            raw_scores.append(sim_pos - (0.5 * sim_neg))

        # In-request relative percentile → 0–100. The mid-rank offset keeps
        # tiny responses meaningful (a single cluster sits at a neutral 50).
        arr = np.asarray(raw_scores, dtype=np.float64)
        order = np.argsort(arr, kind="stable")
        ranks = np.empty(len(order), dtype=np.float64)
        spans = np.arange(len(order), dtype=np.float64)
        ranks[order] = spans
        span = max(len(events), 1)
        for event, rank, score in zip(events, ranks, raw_scores):
            if math.isnan(score) or math.isinf(score):
                event["affinity_pct"] = 50
                continue
            event["affinity_pct"] = int(max(1, min(100, round(100.0 * (rank + 0.5) / span))))

        logger.debug(
            "[AFFINITY] Cluster affinity attached: user=%s events=%s points=%s",
            user_id, len(events), len(vec_map),
        )
    except Exception as e:
        logger.warning("[AFFINITY] Cluster affinity attach failed user=%s: %s", user_id, e)

    return events


# ── Ranked interest terms (top affinities for the user) ───────────────────────

# Term-vector cache in Redis (term embeddings are immutable inputs — the only
# thing that can change them is the embedding model itself, which is part of
# the cache key).
_TERMVEC_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days

_redis_client = None


def _get_termvec_redis():
    """Lazy sync Redis singleton for the term-vector cache (None if down)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis as _redis_mod

        client = _redis_mod.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=0,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        _redis_client = client
    except Exception as e:
        logger.debug("[AFFINITY] Term-vector Redis unavailable: %s", e)
        return None
    return _redis_client


def _termvec_cache_key(term: str) -> str:
    from intelligence.embeddings import MODEL_NAME

    digest = hashlib.sha256(f"{MODEL_NAME}|{term}".encode("utf-8")).hexdigest()[:24]
    return f"affinity:termvec:{digest}"


def _get_term_vectors(terms: list[str]) -> dict[str, np.ndarray]:
    """
    Batched term-embedding lookup shared by every affinity code path that
    needs vectors for several terms (recompute, ranking, migration):
    Redis pipeline read → single batch encode for the misses → Redis
    pipeline write-back. Replaces the old one-encode-per-term loops.

    On a total encode failure the returned dict simply lacks those terms;
    callers decide whether that is fatal (vector recompute) or skippable
    (ranking).
    """
    unique: dict[str, None] = {}  # ordered de-dup (dict keeps insertion order)
    for t in terms:
        t = (t or "").strip()
        if t:
            unique.setdefault(t, None)
    ordered = list(unique)
    if not ordered:
        return {}

    redis = _get_termvec_redis()
    vec_by_term: dict[str, np.ndarray] = {}
    missing: list[str] = []

    if redis is not None:
        try:
            pipe = redis.pipeline(transaction=False)
            for t in ordered:
                pipe.get(_termvec_cache_key(t))
            for t, raw in zip(ordered, pipe.execute()):
                if raw:
                    try:
                        arr = np.array(json.loads(raw), dtype=np.float32)
                        if arr.ndim == 1 and arr.size > 0:
                            vec_by_term[t] = arr
                            continue
                    except (json.JSONDecodeError, ValueError):
                        pass
                missing.append(t)
        except Exception as e:
            logger.debug("[AFFINITY] Term-vector cache read failed: %s", e)
            missing = list(ordered)
    else:
        missing = list(ordered)

    if missing:
        try:
            encoded = _embed_term(missing)
        except Exception as e:
            logger.warning("[AFFINITY] Term batch encode failed: %s", e)
            encoded = None

        if encoded is not None:
            for t, vec in zip(missing, encoded):
                vec_by_term[t] = np.asarray(vec, dtype=np.float32)
            if redis is not None:
                try:
                    pipe = redis.pipeline(transaction=False)
                    for t, vec in zip(missing, encoded):
                        pipe.set(
                            _termvec_cache_key(t),
                            json.dumps(np.asarray(vec, dtype=np.float32).tolist()),
                            ex=_TERMVEC_TTL_SECONDS,
                        )
                    pipe.execute()
                except Exception as e:
                    logger.debug("[AFFINITY] Term-vector cache write failed: %s", e)

    return vec_by_term


def _collect_candidate_terms(user_id: int) -> list[str]:
    """
    Interest vocabulary: the user's manually boosted terms + smart tags.

    Boosted terms come first (explicit user intent — they must never be
    truncated away), then smart tags; both in deterministic alphabetical
    order so the 200-candidate cap is stable across runs instead of
    depending on DB result order.
    """
    terms: list[str] = []
    seen: set[str] = set()
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT DISTINCT term FROM affinity_boosts "
                "WHERE user_id = %s ORDER BY term",
                (user_id,),
            )
            for r in cursor.fetchall():
                t = (r.get("term") or "").strip()
                if t and t.lower() not in seen:
                    seen.add(t.lower())
                    terms.append(t)

            cursor.execute(
                "SELECT name FROM smart_tags WHERE user_id = %s ORDER BY name",
                (user_id,),
            )
            for r in cursor.fetchall():
                name = (r.get("name") or "").strip()
                if name and name.lower() not in seen:
                    seen.add(name.lower())
                    terms.append(name)
        finally:
            cursor.close()
    return terms[:200]


def rank_user_terms(user_id: int, limit: int = 15) -> dict:
    """
    Rank interest terms (smart tags + boosted terms) by how well they match
    the user's profile. Ordering uses the RAW contrast score (unbounded, so
    the ranking keeps discriminating even when display scores cluster near
    100); the displayed affinity is the calibrated logistic remap.
    """
    limit = max(1, min(int(limit), 50))

    row = _get_user_rows(user_id)
    if not row:
        return {"terms": [], "has_profile": False}

    eff_pos, eff_neg = _effective_profile_vectors(row)
    if eff_pos is None:
        return {"terms": [], "has_profile": False}

    candidates = _collect_candidate_terms(user_id)
    if not candidates:
        return {"terms": [], "has_profile": True}

    # ── Term vectors: shared Redis-cached batched lookup ─────────────────
    vec_by_term = _get_term_vectors(candidates)

    # ── Score + rank by raw contrast ─────────────────────────────────────
    scored: list[dict] = []
    for term, term_vec in vec_by_term.items():
        sim_pos = _sanitise_similarity(float(cosine_similarity(term_vec, eff_pos)))
        sim_neg = (
            _sanitise_similarity(float(cosine_similarity(term_vec, eff_neg)))
            if eff_neg is not None
            else 0.0
        )
        raw = contrast_score(sim_pos, sim_neg)
        if math.isnan(raw) or math.isinf(raw):
            raw = 0.0
        scored.append(
            {
                "term": term,
                "affinity": round(calibrated_affinity(raw, AFFINITY_CAL_MU, AFFINITY_CAL_TAU), 4),
                "sim_pos": round(sim_pos, 4),
                "sim_neg": round(sim_neg, 4),
                "_raw": raw,
            }
        )

    scored.sort(key=lambda x: x["_raw"], reverse=True)
    for entry in scored:
        entry.pop("_raw")
    return {"terms": scored[:limit], "has_profile": True}
