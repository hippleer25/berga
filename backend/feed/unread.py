"""
unread.py — Per-feed unread article counts.

An article counts as unread when it was published within the user's
configured time window (0 = since the beginning) and has NO interaction row
with any of the user's configured "read" actions (default: everything
except ``saved``). Article ids come from the Qdrant index (payload
``feed_sha256``); read ids come from the MySQL ``interactions`` table.

Counts are cached in a per-user Redis key with a short TTL so scrolling
the timeline stays cheap; the cache is invalidated eagerly on every
interaction that may affect the configured action set. Everything is
best-effort and fail-open: Redis/Qdrant/MySQL outages return empty counts
so the UI simply hides the badges.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Must match the interactions table ENUM (database/init_db.py).
ALL_ACTIONS = ("like", "dislike", "view", "saved", "read")

# Default semantics: every interaction except `saved` marks an article as read.
DEFAULT_READ_ACTIONS = ("like", "dislike", "view", "read")
DEFAULT_WINDOW_DAYS = 30
MAX_WINDOW_DAYS = 3650

_PREF_WINDOW_KEY = "unread_window_days"
_PREF_ACTIONS_KEY = "unread_read_actions"

_CACHE_KEY = "berga:unread:{user_id}"
_CACHE_TTL = 60  # seconds

_SCROLL_PAGE = 1000

_REDIS_HOST = os.getenv("REDIS_HOST", "redis")
_REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
_REDIS_DB = int(os.getenv("REDIS_DB", "0"))


def _get_client():
    import redis

    try:
        client = redis.Redis(
            host=_REDIS_HOST,
            port=_REDIS_PORT,
            db=_REDIS_DB,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
        client.ping()
        return client
    except Exception as e:
        logger.warning("Redis unavailable for unread counts: %s", e)
        return None


def _coerce_window(raw) -> int:
    """Clamp the window to a sane int; 0 = since the beginning."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_WINDOW_DAYS
    return max(0, min(value, MAX_WINDOW_DAYS))


def _coerce_actions(raw) -> tuple[str, ...]:
    """Filter an arbitrary value down to valid interaction action names."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raw = [raw]
    if not isinstance(raw, (list, tuple)):
        return DEFAULT_READ_ACTIONS
    actions = tuple(a for a in raw if isinstance(a, str) and a in ALL_ACTIONS)
    return actions or DEFAULT_READ_ACTIONS


def get_unread_prefs(user_id: int) -> dict:
    """Read the unread preferences from user_settings (defaults when unset)."""
    from database.init_db import get_db

    rows: dict[str, str] = {}
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT pref_key, pref_value FROM user_settings "
                    "WHERE user_id = %s AND pref_key IN (%s, %s)",
                    (user_id, _PREF_WINDOW_KEY, _PREF_ACTIONS_KEY),
                )
                rows = {k: v for k, v in cursor.fetchall()}
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("Failed to read unread prefs for user %s: %s", user_id, e)

    return {
        "window_days": _coerce_window(rows.get(_PREF_WINDOW_KEY)),
        "read_actions": list(_coerce_actions(rows.get(_PREF_ACTIONS_KEY))),
    }


def set_unread_prefs(user_id: int, window_days, read_actions) -> dict:
    """Persist both unread preferences; invalidates the counts cache."""
    from database.init_db import get_db

    window = _coerce_window(window_days)
    actions = _coerce_actions(read_actions)
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(
                    "INSERT INTO user_settings (user_id, pref_key, pref_value) "
                    "VALUES (%s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE pref_value = VALUES(pref_value)",
                    [
                        (user_id, _PREF_WINDOW_KEY, str(window)),
                        (user_id, _PREF_ACTIONS_KEY, json.dumps(list(actions))),
                    ],
                )
                conn.commit()
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("Failed to store unread prefs for user %s: %s", user_id, e)
        return {"status": "error", "message": str(e)}

    invalidate_unread_cache(user_id)
    return {"status": "ok", "window_days": window, "read_actions": list(actions)}


def get_unread_counts(user_id: int) -> dict:
    """Per-feed unread counts (Redis-cached, recomputed on miss)."""
    client = _get_client()
    cache_key = _CACHE_KEY.format(user_id=user_id)
    if client:
        try:
            raw = client.get(cache_key)
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.warning("Failed to read unread cache for user %s: %s", user_id, e)

    prefs = get_unread_prefs(user_id)
    counts, total = _compute_unread(user_id, prefs)
    payload = {
        "counts": counts,
        "total": total,
        "window_days": prefs["window_days"],
        "read_actions": prefs["read_actions"],
    }

    if client:
        try:
            client.set(cache_key, json.dumps(payload), ex=_CACHE_TTL)
        except Exception as e:
            logger.warning("Failed to cache unread counts for user %s: %s", user_id, e)
    return payload


def _compute_unread(user_id: int, prefs: dict) -> tuple[dict[str, int], int]:
    """Unread articles per subscribed feed + grand total."""
    from database.init_db import get_db

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT feed_sha256 FROM user_subscriptions WHERE user_id = %s",
                    (user_id,),
                )
                feeds = [str(r[0]) for r in cursor.fetchall()]

                actions = prefs["read_actions"]
                fmt = ",".join(["%s"] * len(actions))
                cursor.execute(
                    f"SELECT DISTINCT item_id FROM interactions "
                    f"WHERE user_id = %s AND action IN ({fmt})",
                    (user_id, *actions),
                )
                read_ids = {str(r[0]) for r in cursor.fetchall()}
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("Failed to load unread inputs for user %s: %s", user_id, e)
        return {}, 0

    if not feeds:
        return {}, 0

    try:
        from intelligence.embeddings import get_qdrant_client, COLLECTION_NAME
        from qdrant_client.http import models

        client = get_qdrant_client()
        must = [
            models.FieldCondition(
                key="feed_sha256",
                match=models.MatchAny(any=feeds),
            )
        ]
        window = prefs["window_days"]
        if window > 0:
            min_ts = (datetime.now(timezone.utc) - timedelta(days=window)).timestamp()
            must.append(
                models.FieldCondition(
                    key="pub_timestamp",
                    range=models.Range(gte=min_ts),
                )
            )

        counts = {f: 0 for f in feeds}
        total = 0
        offset = None
        while True:
            points, offset = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=models.Filter(must=must),
                limit=_SCROLL_PAGE,
                offset=offset,
                with_payload=["feed_sha256"],
                with_vectors=False,
            )
            for point in points:
                feed = (point.payload or {}).get("feed_sha256")
                if feed in counts and str(point.id) not in read_ids:
                    counts[feed] += 1
                    total += 1
            if offset is None or not points:
                break
        return counts, total
    except Exception as e:
        logger.warning("Qdrant unread scan failed for user %s: %s", user_id, e)
        return {}, 0


def invalidate_unread_cache(user_id: int) -> None:
    """Drop the per-user unread counts cache (called on relevant events)."""
    try:
        client = _get_client()
        if client:
            client.delete(_CACHE_KEY.format(user_id=user_id))
    except Exception as e:
        logger.warning("Failed to invalidate unread cache for user %s: %s", user_id, e)
