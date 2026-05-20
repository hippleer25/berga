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


def _sse_done() -> str:
    return "data: [DONE]\n\n"


class _Status:
    __slots__ = ('phase',)

    def __init__(self, phase: str):
        self.phase = phase
