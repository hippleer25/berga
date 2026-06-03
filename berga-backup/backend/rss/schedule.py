import asyncio

import aiohttp

from database.init_db import get_db
from rss.parser import parse_and_save_feed_async

# Max feeds fetched/parsed simultaneously
MAX_CONCURRENT = 2


async def parse_user_all_async(user_id: int) -> dict:
    """
    Concurrently parses all feeds subscribed by a user.

    Flow per feed:
      1. Semaphore limits to MAX_CONCURRENT active at once
      2. aiohttp fetches raw XML asynchronously (non-blocking)
      3. feedparser + embeddings + DB run in a thread pool (see parser.py)
    """
    # ── Fetch subscribed feed URLs ─────────────────────────────────
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT f.feed_url
            FROM user_subscriptions us
            JOIN feeds f ON us.feed_sha256 = f.feed_sha256
            WHERE us.user_id = %s
        """, (user_id,))
        feed_rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    if not feed_rows:
        return {"status": "success", "feeds_processed": 0, "details": []}

    # ── Concurrent processing ──────────────────────────────────────
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def parse_one(session: aiohttp.ClientSession, feed_url: str) -> dict:
        async with semaphore:
            return await parse_and_save_feed_async(session, feed_url)

    # Single shared aiohttp session for all requests (connection pooling)
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            *[parse_one(session, row["feed_url"]) for row in feed_rows],
            return_exceptions=True,  # one failure won't cancel the others
        )

    # ── Normalize any unexpected exceptions from gather ────────────
    normalized = []
    for row, result in zip(feed_rows, results):
        if isinstance(result, Exception):
            normalized.append({
                "feed_url": row["feed_url"],
                "result": {"status": "error", "message": str(result)},
            })
        else:
            normalized.append(result)

    return {
        "status": "success",
        "feeds_processed": len(normalized),
        "details": normalized,
    }