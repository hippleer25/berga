import re
import logging
from typing import Generator

from post import load
from bs4 import BeautifulSoup
from mota import ai_lib
from mota.chat_sse import _sse_event, _sse_error, _sse_done
from i18n.prompts import get_prompt

logger = logging.getLogger(__name__)


def _truncate_at_boundary(text: str, limit: int) -> str:
    """Truncate text to at most `limit` chars, on a sentence boundary if possible."""
    if len(text) <= limit:
        return text
    chunk = text[:limit]
    last_stop = max(chunk.rfind(". "), chunk.rfind("! "), chunk.rfind("? "))
    if last_stop > limit * 0.7:
        return chunk[: last_stop + 1].rstrip()
    last_space = chunk.rfind(" ")
    if last_space > limit * 0.8:
        return chunk[:last_space].rstrip() + "…"
    return chunk.rstrip() + "…"


def get(item_id: str, user) -> Generator[str, None, None]:
    response = load.get(user["id"], item_id)
    if response is None:
        yield _sse_error("article content could not be fetched")
        yield _sse_done()
        return

    html_text = response.get("content_html") or ""
    if not html_text:
        yield _sse_error("article has no content")
        yield _sse_done()
        return

    soup = BeautifulSoup(html_text, "html.parser")
    clean_text = soup.get_text()
    cut_size_text = _truncate_at_boundary(clean_text, 15000)

    messages = [
        {"role": "system", "content": get_prompt("resume")},
        {"role": "user", "content": cut_size_text},
    ]

    try:
        for chunk in ai_lib.stream_llm_response(messages, max_tokens=150, usage="summarize"):
            if chunk:
                yield _sse_event(chunk)
    except Exception as e:
        logger.error(f"[RESUME] Erro ao gerar resumo: {e}", exc_info=True)
        yield _sse_error(f"Erro ao gerar resumo: {e}")

    yield _sse_done()
