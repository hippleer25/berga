"""
intelligence/cluster_store.py — In-memory cluster reverse index.

The async clustering pipeline (tasks.py → cluster.py) computes event
clusters periodically.  This module stores a reverse index:

    article_id → [similar_article, similar_article, ...]

so the synchronous recommendation engine can look up cluster siblings
without touching Redis.

The index is refreshed every time the clustering pipeline runs
(typically every 6 hours).  Thread-safe via a lock.
"""

from __future__ import annotations

import threading
import logging

logger = logging.getLogger(__name__)

# ── Internal state ─────────────────────────────────────────────────────────────

_lock: threading.Lock = threading.Lock()

# article_id (str) → list of sibling article dicts
_reverse_index: dict[str, list[dict]] = {}

# article_id (str) → cluster summary headline
_cluster_summaries: dict[str, str] = {}


# ── Public API ─────────────────────────────────────────────────────────────────

def build_reverse_index(events: list[dict]) -> dict[str, list[dict]]:
    """
    Build article_id → [similar_articles] mapping from cluster events.

    Each event has the structure:
        {
            "summary": "Some headline",
            "articles": [
                {"item_id": "...", "title": "...", "url": "...",
                 "source": "...", "feed_icon": "...", "published_at": "..."},
                ...
            ]
        }

    Returns the complete reverse index dict.
    """
    index: dict[str, list[dict]] = {}
    summaries: dict[str, str] = {}

    for event in events:
        articles = event.get("articles", [])
        summary = event.get("summary", "")
        article_ids_in_cluster = set()

        for art in articles:
            art_id = art.get("item_id")
            if art_id:
                article_ids_in_cluster.add(art_id)

        for art in articles:
            art_id = art.get("item_id")
            if not art_id:
                continue

            siblings = [
                {
                    "item_id": a.get("item_id"),
                    "title": a.get("title"),
                    "link": a.get("url"),
                    "feed_title": a.get("source"),
                    "feed_icon": a.get("feed_icon"),
                    "published_at": a.get("published_at"),
                }
                for a in articles
                if a.get("item_id") and a.get("item_id") != art_id
            ]

            if siblings:
                index[art_id] = siblings
                if summary:
                    summaries[art_id] = summary

    logger.info(
        "Cluster reverse index built: %d articles with siblings, %d clusters",
        len(index),
        len(set(event.get("summary", "") for event in events)),
    )
    return index, summaries


def set_cluster_index(index: dict[str, list[dict]], summaries: dict[str, str] | None = None) -> None:
    """Replace the in-memory reverse index (called by the async pipeline)."""
    global _reverse_index, _cluster_summaries
    with _lock:
        _reverse_index = index
        _cluster_summaries = summaries or {}
    logger.info("Cluster index updated: %d mapped articles", len(index))


def get_cluster_index() -> dict[str, list[dict]]:
    """Return a snapshot of the current reverse index (thread-safe copy)."""
    with _lock:
        return dict(_reverse_index)


def get_cluster_summaries() -> dict[str, str]:
    """Return a snapshot of cluster summaries per article."""
    with _lock:
        return dict(_cluster_summaries)


def get_siblings(article_id: str) -> list[dict]:
    """Return similar articles for a single article_id, or empty list."""
    with _lock:
        return list(_reverse_index.get(article_id, []))


def clear() -> None:
    """Clear the index (for testing)."""
    global _reverse_index, _cluster_summaries
    with _lock:
        _reverse_index = {}
        _cluster_summaries = {}