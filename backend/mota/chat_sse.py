"""
mota/chat_sse.py — Server-Sent Events formatting and status marker.

Decoupled from chat.py so that any module that needs to emit SSE events
can import these helpers without pulling in the entire chat orchestrator.
"""

from __future__ import annotations

import json


def _sse_event(content: str) -> str:
    if not content:
        return ""
    payload = json.dumps({"content": content}, ensure_ascii=False)
    return f"data: {payload}\n\n"


def _sse_status(status: str) -> str:
    payload = json.dumps({"status": status}, ensure_ascii=False)
    return f"data: {payload}\n\n"


def _sse_error(message: str) -> str:
    payload = json.dumps({"error": message}, ensure_ascii=False)
    return f"data: {payload}\n\n"


def _sse_sources(sources: list[dict]) -> str:
    payload = json.dumps({"sources": sources}, ensure_ascii=False)
    return f"data: {payload}\n\n"


def _sse_done() -> str:
    return "data: [DONE]\n\n"


class _Status:
    __slots__ = ('phase',)

    def __init__(self, phase: str):
        self.phase = phase


class _Sources:
    """Marker for the citation registry to be emitted as a final SSE event."""

    __slots__ = ('entries',)

    def __init__(self, entries: list[dict]):
        self.entries = entries


class _Queries:
    """Marker for the list of search queries executed in this turn."""

    __slots__ = ('queries',)

    def __init__(self, queries: list[str]):
        self.queries = queries


class _Thinking:
    """Marker: provider reasoning_content chunk for the visible thinking panel."""

    __slots__ = ('text',)

    def __init__(self, text: str):
        self.text = text


def _sse_thinking(text: str) -> str:
    payload = json.dumps({"thinking": text}, ensure_ascii=False)
    return f"data: {payload}\n\n"


def _sse_queries(queries: list[str]) -> str:
    payload = json.dumps({"queries": queries}, ensure_ascii=False)
    return f"data: {payload}\n\n"


def _sse_session(session_id: int) -> str:
    payload = json.dumps({"session": {"id": session_id}}, ensure_ascii=False)
    return f"data: {payload}\n\n"


class _Session:
    """Marker: the session id for this conversation, emitted once at turn start."""

    __slots__ = ('id',)

    def __init__(self, id: int):
        self.id = id
