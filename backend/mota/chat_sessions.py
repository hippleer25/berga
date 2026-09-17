"""
mota/chat_sessions.py — Durable chat session store backed by MySQL.

MySQL is the source of truth for sessions (title, messages, sources);
Redis (`mota/conversation.py`) is only the hot working cache, scoped per
session. Nothing here raises for storage failures — every helper fails
open so chat keeps working when the DB is unreachable.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_TITLE_FALLBACK_MAX_CHARS = 48
_LIST_LIMIT = 50


def _db():
    from database.init_db import get_db
    return get_db()


def create_session(user_id: int, first_message: str) -> Optional[int]:
    """Create a session row seeded with the fallback title. Returns id or None."""
    if not user_id:
        return None
    fallback = " ".join((first_message or "").split())[:_TITLE_FALLBACK_MAX_CHARS] or None
    try:
        with _db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO chat_sessions (user_id, fallback_title) VALUES (%s, %s)",
                    (user_id, fallback),
                )
                conn.commit()
                return cursor.lastrowid
            finally:
                cursor.close()
    except Exception as e:
        logger.warning(f"[SESSIONS] Failed to create session user={user_id}: {e}")
        return None


def session_exists(user_id: int, session_id: int) -> bool:
    """Ownership-checked existence test."""
    if not user_id or not session_id:
        return False
    try:
        with _db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT 1 FROM chat_sessions WHERE id = %s AND user_id = %s",
                    (session_id, user_id),
                )
                return cursor.fetchone() is not None
            finally:
                cursor.close()
    except Exception as e:
        logger.warning(f"[SESSIONS] session_exists failed user={user_id} session={session_id}: {e}")
        return False


def get_session(user_id: int, session_id: int) -> Optional[dict]:
    """Fetch a single user-owned session row (dict) or None."""
    if not user_id or not session_id:
        return None
    try:
        with _db() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(
                    """SELECT id, title, fallback_title, message_count,
                              created_at, updated_at
                       FROM chat_sessions
                       WHERE id = %s AND user_id = %s""",
                    (session_id, user_id),
                )
                return cursor.fetchone()
            finally:
                cursor.close()
    except Exception as e:
        logger.warning(f"[SESSIONS] get_session failed user={user_id} session={session_id}: {e}")
        return None


def list_sessions(user_id: int, limit: int = _LIST_LIMIT) -> list[dict]:
    """Most recent sessions by last interaction (updated_at DESC)."""
    if not user_id:
        return []
    try:
        with _db() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(
                    """SELECT id, title, fallback_title, message_count,
                              created_at, updated_at
                       FROM chat_sessions
                       WHERE user_id = %s
                       ORDER BY updated_at DESC
                       LIMIT %s""",
                    (user_id, int(limit)),
                )
                return cursor.fetchall()
            finally:
                cursor.close()
    except Exception as e:
        logger.warning(f"[SESSIONS] list_sessions failed user={user_id}: {e}")
        return []


def rename_session(user_id: int, session_id: int, title: str) -> bool:
    """Set a manual title (overrides the AI title)."""
    if not user_id or not session_id:
        return False
    title = " ".join((title or "").split())[:120]
    if not title:
        return False
    try:
        with _db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE chat_sessions SET title = %s WHERE id = %s AND user_id = %s",
                    (title, session_id, user_id),
                )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                cursor.close()
    except Exception as e:
        logger.warning(f"[SESSIONS] rename failed user={user_id} session={session_id}: {e}")
        return False


def delete_session(user_id: int, session_id: int) -> bool:
    """Delete a session; messages cascade."""
    if not user_id or not session_id:
        return False
    try:
        with _db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "DELETE FROM chat_sessions WHERE id = %s AND user_id = %s",
                    (session_id, user_id),
                )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                cursor.close()
    except Exception as e:
        logger.warning(f"[SESSIONS] delete failed user={user_id} session={session_id}: {e}")
        return False


def append_message(
    user_id: int,
    session_id: int,
    role: str,
    content: str,
    sources: Optional[list[dict]] = None,
) -> None:
    """Persist one turn to chat_messages and bump the session's counters."""
    if not user_id or not session_id:
        return
    if not content or not content.strip():
        return
    try:
        with _db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """INSERT INTO chat_messages (session_id, role, content, sources)
                       VALUES (%s, %s, %s, %s)""",
                    (
                        session_id,
                        role,
                        content,
                        json.dumps(sources, ensure_ascii=False) if sources else None,
                    ),
                )
                cursor.execute(
                    """UPDATE chat_sessions
                       SET message_count = message_count + 1,
                           fallback_title = COALESCE(fallback_title, %s)
                       WHERE id = %s AND user_id = %s""",
                    (
                        (" ".join(content.split())[:_TITLE_FALLBACK_MAX_CHARS] or None)
                        if role == "user" else None,
                        session_id,
                        user_id,
                    ),
                )
                conn.commit()
            finally:
                cursor.close()
    except Exception as e:
        logger.warning(f"[SESSIONS] append_message failed session={session_id}: {e}")


def get_messages(user_id: int, session_id: int) -> list[dict]:
    """Full turn log for a user-owned session, oldest first.

    Turns follow the conversation.py shape: {role, content, sources?}.
    """
    if not user_id or not session_id:
        return []
    try:
        with _db() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(
                    """SELECT m.role, m.content, m.sources
                       FROM chat_messages m
                       JOIN chat_sessions s ON s.id = m.session_id
                       WHERE s.user_id = %s AND m.session_id = %s
                       ORDER BY m.id ASC""",
                    (user_id, session_id),
                )
                rows = cursor.fetchall()
            finally:
                cursor.close()
        turns = []
        for row in rows:
            turn: dict = {"role": row["role"], "content": row["content"] or ""}
            if row.get("sources"):
                try:
                    sources = json.loads(row["sources"])
                    if isinstance(sources, list):
                        turn["sources"] = sources
                except Exception:
                    pass
            turns.append(turn)
        return turns
    except Exception as e:
        logger.warning(f"[SESSIONS] get_messages failed session={session_id}: {e}")
        return []


def set_ai_title(user_id: int, session_id: int, title: str) -> bool:
    """Write the AI-generated title (used by the arq title job).

    Never overwrites a manually set title when the new value is empty.
    """
    if not user_id or not session_id:
        return False
    title = " ".join((title or "").split())[:120]
    if not title:
        return False
    try:
        with _db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE chat_sessions SET title = %s WHERE id = %s AND user_id = %s",
                    (title, session_id, user_id),
                )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                cursor.close()
    except Exception as e:
        logger.warning(f"[SESSIONS] set_ai_title failed session={session_id}: {e}")
        return False


def get_title_seed(user_id: int, session_id: int) -> Optional[str]:
    """First user message of a session, used to seed title generation."""
    if not user_id or not session_id:
        return None
    try:
        with _db() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(
                    """SELECT m.content
                       FROM chat_messages m
                       JOIN chat_sessions s ON s.id = m.session_id
                       WHERE s.user_id = %s AND s.id = %s AND m.role = 'user'
                       ORDER BY m.id ASC
                       LIMIT 1""",
                    (user_id, session_id),
                )
                row = cursor.fetchone()
            finally:
                cursor.close()
        return (row or {}).get("content")
    except Exception as e:
        logger.warning(f"[SESSIONS] get_title_seed failed session={session_id}: {e}")
        return None


def session_title(user_id: int, session_id: int) -> Optional[str]:
    """Current display title (manual/AI) or None when unchanged."""
    session = get_session(user_id, session_id)
    if not session:
        return None
    return session.get("title") or session.get("fallback_title")
