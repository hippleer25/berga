"""
mota/conversation.py — Per-session conversation memory backed by Redis + MySQL.

Two layers:
  1. Raw turn log   (`mota:conv:{user_id}:{session_id}`) — JSON list of turns,
     24h TTL, capped at MAX_TURNS. Assistant text is stored truncated to bound
     memory. Each assistant turn may carry `sources`, so follow-up questions
     like "what does [3] mean?" or "that article" keep working.
  2. Prompt history (`prepare_history`)          — token-budgeted view of the
     log: the most recent HISTORY_VERBATIM_TURNS turns are kept verbatim,
     everything older is folded into a single summary block (SUMMARIZE tier,
     cached in Redis for SUMMARY_CACHE_TTL_SECONDS).

MySQL (`mota/chat_sessions.py`) is the durable source of truth: when the
Redis hot cache is empty for a session (TTL expiry, restart), it is
re-hydrated from `chat_messages` on demand.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Optional

import redis

from mota.tokens import count_tokens
from mota.chat_config import (
    HISTORY_TOKEN_BUDGET,
    HISTORY_VERBATIM_TURNS,
)

logger = logging.getLogger(__name__)

_REDIS_HOST = os.getenv("REDIS_HOST", "redis")
_REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
_REDIS_DB = int(os.getenv("REDIS_DB", "0"))

_TTL_SECONDS = 24 * 3600  # 24 hours
MAX_TURNS = 12  # max messages stored raw (6 user + 6 assistant pairs)
_ASSISTANT_MAX_CHARS = 2000  # truncate stored assistant responses
_SUMMARY_MAX_TOKENS = 400
_SOURCES_MAX = 10

_client: Optional[redis.Redis] = None

from mota.chat_config import SUMMARY_CACHE_TTL_SECONDS


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


def _key(user_id: int, session_id) -> str:
    return f"mota:conv:{user_id}:{session_id}"


def _summary_key(user_id: int, session_id) -> str:
    return f"mota:conv:{user_id}:{session_id}:summary"


def _sources_key(user_id: int, session_id) -> str:
    return f"mota:conv:{user_id}:{session_id}:sources"


# ── MySQL hydration ───────────────────────────────────────────────────────────

def _hydrate_from_db(user_id: int, session_id) -> list[dict]:
    """Load the durable turn log for a session and seed the Redis cache.

    Called when the hot cache is empty but the session exists in MySQL
    (Redis TTL expired, server restart, resume on another device).
    Fails open with [] on any error.
    """
    try:
        from mota import chat_sessions
        turns = chat_sessions.get_messages(user_id, session_id)
    except Exception as e:
        logger.warning(f"[CONV] Hydration failed user={user_id} session={session_id}: {e}")
        return []
    if not turns:
        return []
    client = _get_client()
    if client is not None:
        try:
            trimmed = turns[-MAX_TURNS:]
            client.setex(
                _key(user_id, session_id),
                _TTL_SECONDS,
                json.dumps(trimmed, ensure_ascii=False),
            )
            sources: list[dict] = []
            for t in trimmed:
                if t.get("role") == "assistant" and t.get("sources"):
                    sources = t["sources"]
            if sources:
                client.setex(
                    _sources_key(user_id, session_id),
                    _TTL_SECONDS,
                    json.dumps(sources[-_SOURCES_MAX:], ensure_ascii=False),
                )
        except Exception as e:
            logger.warning(f"[CONV] Failed to seed cache from DB session={session_id}: {e}")
    return turns


# ── Raw turn log ──────────────────────────────────────────────────────────────

def load_history(user_id: int, session_id=None) -> list[dict]:
    """Load raw conversation turns for a session. Returns [] on any failure.

    Falls back to MySQL-backed hydration when the Redis cache is empty.
    """
    client = _get_client()
    if client is None or session_id is None:
        return []
    try:
        raw = client.get(_key(user_id, session_id))
        if not raw:
            return _hydrate_from_db(user_id, session_id)
        history = json.loads(raw)
        if isinstance(history, list):
            return [t for t in history if isinstance(t, dict) and t.get("role") and t.get("content")]
        return []
    except Exception as e:
        logger.warning(f"[CONV] Failed to load history user={user_id} session={session_id}: {e}")
        return []


def save_turn(
    user_id: int, role: str, content: str,
    sources: Optional[list[dict]] = None, session_id=None,
) -> None:
    """
    Append a turn to the session's conversation history.

    Truncates assistant content to bound memory. Trims to the last
    MAX_TURNS messages. Refreshes the TTL. `sources` (assistant turns only)
    stores the numbered citation registry entries used by that answer.
    Durable persistence to MySQL happens in chat.py (`_persist_turn`),
    not here.
    """
    if not content or not content.strip():
        return

    client = _get_client()
    if client is None or session_id is None:
        return

    if role == "assistant" and len(content) > _ASSISTANT_MAX_CHARS:
        content = content[:_ASSISTANT_MAX_CHARS].rstrip() + "…"

    turn: dict = {"role": role, "content": content}
    if sources:
        turn["sources"] = sources

    try:
        history = load_history(user_id, session_id)
        history.append(turn)
        if len(history) > MAX_TURNS:
            history = history[-MAX_TURNS:]
        client.setex(
            _key(user_id, session_id), _TTL_SECONDS,
            json.dumps(history, ensure_ascii=False),
        )
    except Exception as e:
        logger.warning(f"[CONV] Failed to save turn user={user_id} session={session_id}: {e}")


def clear(user_id: int, session_id=None) -> bool:
    """Clear a session's history + summary cache + sources."""
    client = _get_client()
    if client is None or session_id is None:
        return False
    try:
        client.delete(_key(user_id, session_id), _summary_key(user_id, session_id), _sources_key(user_id, session_id))
        logger.info(f"[CONV] Cleared history user={user_id} session={session_id}")
        return True
    except Exception as e:
        logger.warning(f"[CONV] Failed to clear history user={user_id} session={session_id}: {e}")
        return False


# ── Token-budgeted prompt history ────────────────────────────────────────────

def _history_fingerprint(turns: list[dict]) -> str:
    if not turns:
        return "0"
    joined = "\n".join(t.get("content", "")[:120] for t in turns)
    return hashlib.md5(joined.encode("utf-8", "ignore")).hexdigest()


def _summarize_older(turns: list[dict]) -> str:
    """Summarize a list of older turns into a compact paragraph. Never raises."""
    lines = []
    for t in turns:
        label = "User" if t.get("role") == "user" else "Mota"
        lines.append(f"{label}: {t.get('content', '')[:800]}")
    text = "\n".join(lines)
    try:
        from i18n.prompts import get_prompt
        from mota.ai_lib import generate_text
        summary = generate_text(
            text,
            system_prompt=get_prompt("history_summary"),
            usage="summarize",
            max_tokens=_SUMMARY_MAX_TOKENS,
            temperature=0.1,
        )
        if summary:
            return summary.strip()
    except Exception as e:
        logger.warning(f"[CONV] History summarization failed: {e}")
    # Crude fallback: first sentence fragments
    return "\n".join(lines[-4:])[:1200]


def prepare_history(user_id: int, session_id=None) -> list[dict]:
    """
    Build the prompt-ready history message list within HISTORY_TOKEN_BUDGET.

    Returns messages like:
      [{"role": "system"-equivalent summary as first user-adjacent block}, ...]
    Summary is injected as a system message at the front, labeled as context.
    """
    history = load_history(user_id, session_id)
    if not history:
        return []

    total = count_tokens(json.dumps(history, ensure_ascii=False))
    if total <= HISTORY_TOKEN_BUDGET:
        # Strip sources payload — not needed for prompts
        return [{"role": t["role"], "content": t["content"]} for t in history]

    # Over budget: keep the tail verbatim, summarize the head
    verbatim = history[-HISTORY_VERBATIM_TURNS:]
    older = history[:-HISTORY_VERBATIM_TURNS]
    if not older:
        return [{"role": t["role"], "content": t["content"]} for t in verbatim]

    client = _get_client()
    summary_text: Optional[str] = None
    fingerprint = _history_fingerprint(older)

    if client is not None:
        try:
            raw = client.get(_summary_key(user_id, session_id))
            if raw:
                cached = json.loads(raw)
                if cached.get("fingerprint") == fingerprint:
                    summary_text = cached.get("text")
        except Exception:
            pass

    if summary_text is None:
        summary_text = _summarize_older(older)
        if client is not None:
            try:
                client.setex(
                    _summary_key(user_id, session_id),
                    SUMMARY_CACHE_TTL_SECONDS,
                    json.dumps({"fingerprint": fingerprint, "text": summary_text},
                               ensure_ascii=False),
                )
            except Exception:
                pass

    messages = [{"role": "system", "content": f"Context from earlier in this conversation (summarized):\n{summary_text}"}]
    messages.extend({"role": t["role"], "content": t["content"]} for t in verbatim)
    return messages


def digest_for_router(user_id: int, session_id=None, max_chars: int = 1200) -> str:
    """
    Compact text digest of the last few turns, used as router context.
    Returns "" when there is no history.
    """
    history = load_history(user_id, session_id)
    if not history:
        return ""
    lines = []
    for t in history[-4:]:
        label = "User" if t.get("role") == "user" else "Mota"
        lines.append(f"{label}: {t.get('content', '')[:300]}")
    digest = "\n".join(lines)
    return digest[-max_chars:]


# ── Source registry persistence ──────────────────────────────────────────────

def load_sources(user_id: int, session_id=None) -> list[dict]:
    """Load the most recent numbered source registry for a session."""
    client = _get_client()
    if client is None or session_id is None:
        return []
    try:
        raw = client.get(_sources_key(user_id, session_id))
        if not raw:
            return []
        entries = json.loads(raw)
        return entries if isinstance(entries, list) else []
    except Exception as e:
        logger.warning(f"[CONV] Failed to load sources user={user_id} session={session_id}: {e}")
        return []


def save_sources(user_id: int, sources: list[dict], session_id=None) -> None:
    """Store the current numbered source registry (capped, TTL-refreshed)."""
    client = _get_client()
    if client is None or session_id is None or not sources:
        return
    try:
        trimmed = sources[-_SOURCES_MAX:]
        client.setex(
            _sources_key(user_id, session_id), _TTL_SECONDS,
            json.dumps(trimmed, ensure_ascii=False),
        )
    except Exception as e:
        logger.warning(f"[CONV] Failed to save sources user={user_id} session={session_id}: {e}")


# ── Daily token guardrail ────────────────────────────────────────────────────

def _daily_tokens_key(user_id: int) -> str:
    from datetime import datetime, timezone
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"mota:tokens:{user_id}:{day}"


def add_token_usage(user_id: int, usage: dict) -> int:
    """
    Accrue approximate token usage for today's chat usage counter.
    `usage` maps category → tokens (router/loop/evidence/answer).
    Returns the new daily total; -1 when Redis is unavailable.
    """
    client = _get_client()
    if client is None or not usage:
        return -1
    total = 0
    for v in usage.values():
        try:
            total += int(v)
        except (TypeError, ValueError):
            continue
    if total <= 0:
        return daily_tokens(user_id)
    try:
        key = _daily_tokens_key(user_id)
        client.incrby(key, total)
        client.expire(key, 172800)  # 48h, spans the daily rotation
        return daily_tokens(user_id)
    except Exception as e:
        logger.warning(f"[CONV] Failed to accrue token usage user={user_id}: {e}")
        return -1


def daily_tokens(user_id: int) -> int:
    """Today's accumulated chat token usage. 0 when Redis is unavailable."""
    client = _get_client()
    if client is None:
        return 0
    try:
        raw = client.get(_daily_tokens_key(user_id))
        return int(raw or 0)
    except Exception as e:
        logger.warning(f"[CONV] Failed to read token usage user={user_id}: {e}")
        return 0
