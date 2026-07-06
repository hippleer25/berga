import re
import logging
from typing import Generator

from post import load
from bs4 import BeautifulSoup
from mota import ai_lib
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
        yield "data: Error: article content could not be fetched.\n\n"
        yield "data: [DONE]\n\n"
        return

    html_text = response.get("content_html") or ""
    if not html_text:
        yield "data: Error: article has no content.\n\n"
        yield "data: [DONE]\n\n"
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
            yield f"data: {chunk}\n\n"
    except Exception as e:
        logger.error(f"[RESUME] Erro ao gerar resumo: {e}", exc_info=True)
        yield f"data: {{\"error\": \"Erro ao gerar resumo: {e}\"}}\n\n"

    yield "data: [DONE]\n\n"
