"""
mota/conversation.py — Per-user conversation memory backed by Redis.

Stores recent turns so the chat can maintain context across follow-up
questions. One conversation per user (latest wins), 24h TTL, capped
at MAX_TURNS messages. Assistant content is truncated to bound memory.

Key format: mota:conv:{user_id}
Value: JSON list of {"role": "user"|"assistant", "content": str}
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

import redis

logger = logging.getLogger(__name__)

_REDIS_HOST = os.getenv("REDIS_HOST", "redis")
_REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
_REDIS_DB = int(os.getenv("REDIS_DB", "0"))

_TTL_SECONDS = 24 * 3600  # 24 hours
MAX_TURNS = 12  # max messages stored (6 user + 6 assistant pairs)
_ASSISTANT_MAX_CHARS = 2000  # truncate stored assistant responses

_client: Optional[redis.Redis] = None


def _get_client() -> Optional[redis.Redis]:
    """Lazy singleton for the sync Redis client. Returns None if unreachable."""
    global _client
    if _client is not None:
        return _client
    try:
        _client = redis.Redis(
            host=_REDIS_HOST,
            port=_REDIS_PORT,
            db=_REDIS_DB,
            socket_connect_timeout=3,
            socket_timeout=3,
            decode_responses=True,
        )
        _client.ping()
        logger.info(f"[CONV] Redis connected at {_REDIS_HOST}:{_REDIS_PORT}")
    except Exception as e:
        logger.warning(f"[CONV] Redis unavailable, conversation memory disabled: {e}")
        _client = None
    return _client


def _key(user_id: int) -> str:
    return f"mota:conv:{user_id}"


def load_history(user_id: int) -> list[dict]:
    """Load conversation history for a user. Returns [] on any failure."""
    client = _get_client()
    if client is None:
        return []
    try:
        raw = client.get(_key(user_id))
        if not raw:
            return []
        history = json.loads(raw)
        if isinstance(history, list):
            return history
        return []
    except Exception as e:
        logger.warning(f"[CONV] Failed to load history for user={user_id}: {e}")
        return []


def save_turn(user_id: int, role: str, content: str) -> None:
    """
    Append a turn to the user's conversation history.

    Truncates assistant content to bound memory. Trims to the last
    MAX_TURNS messages. Refreshes the TTL.
    """
    if not content or not content.strip():
        return

    client = _get_client()
    if client is None:
        return

    if role == "assistant" and len(content) > _ASSISTANT_MAX_CHARS:
        content = content[:_ASSISTANT_MAX_CHARS].rstrip() + "…"

    turn = {"role": role, "content": content}

    try:
        history = load_history(user_id)
        history.append(turn)
        if len(history) > MAX_TURNS:
            history = history[-MAX_TURNS:]
        client.setex(_key(user_id), _TTL_SECONDS, json.dumps(history))
    except Exception as e:
        logger.warning(f"[CONV] Failed to save turn for user={user_id}: {e}")


def clear(user_id: int) -> bool:
    """Clear conversation history for a user. Returns True on success."""
    client = _get_client()
    if client is None:
        return False
    try:
        client.delete(_key(user_id))
        logger.info(f"[CONV] Cleared history for user={user_id}")
        return True
    except Exception as e:
        logger.warning(f"[CONV] Failed to clear history for user={user_id}: {e}")
        return False
