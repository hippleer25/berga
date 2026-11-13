"""
utils/profile_pack/pack_export.py — "bergapack" export of a user's
recommendation profile.

A bergapack is a portable JSON snapshot of everything that makes a
user's feed *theirs*: the interaction-learned pos/neg vectors, the
publisher engagement counters and the raw manual affinity boost
history. Derived data is intentionally left out — publisher_freq is
recomputed daily from the corpus and the affinity direction vectors
are rebuilt from the boost rows on import, in the *target* instance's
embedding model.

The pack embeds the embedding-model fingerprint so the importer can
decide whether the learned vectors are usable or must be dropped for
gradual re-learning (boosts + publisher counters are always usable).
"""

import json
import logging
from datetime import datetime, timezone

from fastapi.responses import Response

from database.init_db import get_db
from intelligence.embeddings import (
    MODEL_NAME,
    VECTOR_SIZE,
    get_embedding_model,
    get_current_fingerprint,
    compute_model_fingerprint,
)

logger = logging.getLogger(__name__)

PACK_FORMAT = "bergapack"
PACK_VERSION = 1


def _current_model_fingerprint() -> str:
    """Stable fingerprint of the running embedding model (lazily forces the model load)."""
    fp = get_current_fingerprint()
    if fp:
        return fp
    return compute_model_fingerprint(get_embedding_model())


def _safe_json_loads(raw: str | None, default):
    if not raw:
        return default
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, (dict, list)) else default
    except (json.JSONDecodeError, ValueError):
        return default


def export(user: dict) -> Response:
    user_id = user["id"]
    username = user.get("username") or ""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT pos_vector, neg_vector,
                   publisher_likes, publisher_dislikes
            FROM user_vectors WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cursor.fetchone()

        cursor.execute(
            """
            SELECT term, direction, strength, created_at
            FROM affinity_boosts WHERE user_id = %s
            ORDER BY created_at, term
            """,
            (user_id,),
        )
        boosts = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    vectors: dict = {
        "pos_vector": None,
        "neg_vector": None,
        "publisher_likes": {},
        "publisher_dislikes": {},
    }
    if row:
        pos = _safe_json_loads(row.get("pos_vector"), [])
        neg = _safe_json_loads(row.get("neg_vector"), [])
        # '[]' is the schema's "no vector yet" placeholder — export NULL instead.
        vectors["pos_vector"] = pos if pos else None
        vectors["neg_vector"] = neg if neg else None
        vectors["publisher_likes"] = _safe_json_loads(row.get("publisher_likes"), {})
        vectors["publisher_dislikes"] = _safe_json_loads(row.get("publisher_dislikes"), {})

    pack = {
        "format": PACK_FORMAT,
        "version": PACK_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "username": username,
        "model": {
            "name": MODEL_NAME,
            "vector_size": VECTOR_SIZE,
            "fingerprint": _current_model_fingerprint(),
        },
        "vectors": vectors,
        "affinity_boosts": [
            {
                "term": b["term"],
                "direction": b["direction"],
                "strength": float(b["strength"]),
                "created_at": b["created_at"].isoformat() if b.get("created_at") else None,
            }
            for b in boosts
        ],
    }

    body = json.dumps(pack, ensure_ascii=False, indent=2).encode("utf-8")
    safe_name = "".join(c for c in username if c.isalnum() or c in "-_") or "user"

    logger.info(
        "Profile pack exported: user=%s vectors=%s boosts=%s",
        user_id, bool(vectors.get("pos_vector")), len(pack["affinity_boosts"]),
    )

    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="bergapack-{safe_name}.json"'},
    )
