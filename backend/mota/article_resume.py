import re
import logging
from typing import Generator

from post import load
from bs4 import BeautifulSoup
from mota import ai_lib

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a summarization assistant.
Summarize the article content in a maximum of 50 words.
Respond with plain text only, no markdown, no JSON, no headers.
"""


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
    cut_size_text = clean_text[:15000]

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": cut_size_text},
    ]

    try:
        for chunk in ai_lib.stream_llm_response(messages, max_tokens=300):
            yield f"data: {chunk}\n\n"
    except Exception as e:
        logger.error(f"[RESUME] Erro ao gerar resumo: {e}", exc_info=True)
        yield f"data: {{\"error\": \"Erro ao gerar resumo: {e}\"}}\n\n"

    yield "data: [DONE]\n\n"
