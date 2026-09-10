"""
mota/wiki.py — Free background-knowledge lookup via Wikipedia REST APIs.

Used for encyclopedia-style questions ("who is X", "how does Y work") where
news articles alone give poor grounding. No extra dependencies or API keys.

Endpoints used (both anonymous, generous limits):
  - /w/api.php?action=query&list=search       → resolve best page title
  - /api/rest_v1/page/summary/{title}         → short conceptual summary
"""

from __future__ import annotations

import logging

import requests

from mota.chat_config import WIKI_EXTRACT_CHARS, WIKI_TIMEOUT

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "BergaRSS/1.0 (news assistant; +https://github.com)"}


def search_title(query: str, lang: str = "en") -> str | None:
    url = f"https://{lang}.wikipedia.org/w/api.php"
    try:
        resp = requests.get(
            url,
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": 1,
                "format": "json",
            },
            headers=_UA,
            timeout=WIKI_TIMEOUT,
        )
        resp.raise_for_status()
        hits = resp.json().get("query", {}).get("search", [])
        return hits[0]["title"] if hits else None
    except Exception as e:
        logger.warning(f"[WIKI] Search failed for {query!r} ({lang}): {e}")
        return None


def summary_for_title(title: str, lang: str = "en") -> dict | None:
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
    try:
        resp = requests.get(url, headers=_UA, timeout=WIKI_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        extract = data.get("extract")
        if not extract:
            return None
        return {
            "title": data.get("title") or title,
            "extract": extract[:WIKI_EXTRACT_CHARS],
            "url": data.get("content_urls", {}).get("desktop", {}).get("page")
            or f"https://{lang}.wikipedia.org/wiki/{title}",
        }
    except Exception as e:
        logger.warning(f"[WIKI] Summary failed for {title!r} ({lang}): {e}")
        return None


def fetch_background(query: str, lang: str = "en") -> dict | None:
    """
    Returns {'title': ..., 'extract': ..., 'url': ...} for the best matching
    Wikipedia page, or None. Tries the requested language first, then English.
    """
    try:
        for language in [lang, "en"] if lang != "en" else ["en"]:
            title = search_title(query, language)
            if not title:
                continue
            page = summary_for_title(title, language)
            if page:
                return page
    except Exception as e:  # never blow up the chat turn over a wiki hiccup
        logger.warning(f"[WIKI] Background fetch failed: {e}")
    return None
