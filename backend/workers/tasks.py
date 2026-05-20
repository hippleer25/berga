"""
tasks.py — Background job definitions for the arq worker.
"""

import asyncio
import aiohttp
import logging
import os
from database.init_db import get_db
from rss.parser import parse_and_save_feed_async
from intelligence.cluster import compute_weekly_events, set_cached_events
from intelligence.cluster_store import build_reverse_index, set_cluster_index
from arq import cron
from arq.connections import RedisSettings

logger = logging.getLogger(__name__)

MAX_CONCURRENT = int(os.getenv("FEED_PARSE_MAX_CONCURRENT", "2"))
STALE_HOURS = int(os.getenv("FEED_STALE_HOURS", "6"))
REFRESH_CRON_HOURS = {int(h) for h in os.getenv("FEED_REFRESH_CRON_HOURS", "0,6,12,18").split(",")}


# ── Feed refresh ───────────────────────────────────────────────────────────────

def _get_stale_feeds_sync() -> list[dict]:
    """Synchronous DB call to get stale feeds."""
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(f"""
                SELECT feed_url, feed_sha256 FROM feeds
                WHERE last_parsed_at < NOW() - INTERVAL {STALE_HOURS} HOUR
                   OR last_parsed_at IS NULL
            """)
            return cursor.fetchall()
        finally:
            cursor.close()


async def refresh_stale_feeds(ctx):
    """Parse all feeds not updated in the last 6 hours."""
    stale = await asyncio.to_thread(_get_stale_feeds_sync)

    if not stale:
        return {"refreshed": 0}

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def parse_one(session, feed_url):
        async with semaphore:
            return await parse_and_save_feed_async(session, feed_url)

    async with aiohttp.ClientSession() as session:
        await asyncio.gather(
            *[parse_one(session, row["feed_url"]) for row in stale],
            return_exceptions=True,
        )

    stale_hashes = [row["feed_sha256"] for row in stale if row.get("feed_sha256")]
    if stale_hashes:
        await _refresh_freq_for_affected_users(stale_hashes)

    return {"refreshed": len(stale)}


def _get_affected_users_and_feeds_sync(stale_feed_hashes: list[str]) -> dict[int, list[str]]:
    """Synchronous DB call to find users affected by stale feeds."""
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            fmt = ",".join(["%s"] * len(stale_feed_hashes))
            cursor.execute(
                f"""
                SELECT DISTINCT user_id
                FROM user_subscriptions
                WHERE feed_sha256 IN ({fmt})
                """,
                stale_feed_hashes,
            )
            affected_users = [row["user_id"] for row in cursor.fetchall()]

            if not affected_users:
                return {}

            user_feeds: dict[int, list[str]] = {}
            for user_id in affected_users:
                cursor.execute(
                    "SELECT feed_sha256 FROM user_subscriptions WHERE user_id = %s",
                    (user_id,),
                )
                user_feeds[user_id] = [r["feed_sha256"] for r in cursor.fetchall()]
            return user_feeds
        finally:
            cursor.close()


async def _refresh_freq_for_affected_users(stale_feed_hashes: list[str]) -> None:
    """Recalculate publisher_freq for users subscribed to changed feeds."""
    from database.qdrant_utils import refresh_publisher_freq

    if not stale_feed_hashes:
        return

    user_feeds = await asyncio.to_thread(_get_affected_users_and_feeds_sync, stale_feed_hashes)

    if not user_feeds:
        return

    updated = 0
    for user_id, feed_hashes in user_feeds.items():
        try:
            await asyncio.to_thread(refresh_publisher_freq, user_id, feed_hashes)
            updated += 1
        except Exception as exc:
            logger.error(
                "Error updating publisher_freq for user_id=%s: %s", user_id, exc
            )

    logger.info(
        "publisher_freq updated for %d/%d affected users",
        updated,
        len(user_feeds),
    )


# ── Daily sliding-window refresh ──────────────────────────────────────────────

def _get_all_user_feeds_sync() -> list[dict]:
    """Synchronous DB call to get all users and their feeds."""
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT us.user_id,
                    SUBSTRING_INDEX(GROUP_CONCAT(us.feed_sha256 SEPARATOR ','), ',', 500) AS feeds
                FROM user_subscriptions us
                INNER JOIN user_vectors uv ON uv.user_id = us.user_id
                GROUP BY us.user_id
                """
            )
            return cursor.fetchall()
        finally:
            cursor.close()


async def refresh_all_publisher_freq(ctx):
    """Recalculate publisher_freq for ALL active users (daily job)."""
    from database.qdrant_utils import refresh_publisher_freq

    rows = await asyncio.to_thread(_get_all_user_feeds_sync)

    if not rows:
        return {"updated": 0}

    updated = 0
    for row in rows:
        feed_hashes = row["feeds"].split(",") if row["feeds"] else []
        if not feed_hashes:
            continue
        try:
            await asyncio.to_thread(refresh_publisher_freq, row["user_id"], feed_hashes)
            updated += 1
        except Exception as exc:
            logger.error(
                "refresh_all_publisher_freq failed for user_id=%s: %s",
                row["user_id"],
                exc,
            )

    logger.info("refresh_all_publisher_freq complete: %d users updated", updated)
    return {"updated": updated}


# ── Other jobs ─────────────────────────────────────────────────────────────────



async def parse_feeds_for_user(ctx, user_id: int):
    """Triggered after OPML import to parse newly added feeds."""
    from rss.schedule import parse_user_all_async
    result = await parse_user_all_async(user_id)
    errors = [d for d in result.get("details", []) if d.get("result", {}).get("status") == "error"]
    if errors:
        logger.warning(
            "parse_feeds_for_user(user=%d): %d/%d feeds failed: %s",
            user_id, len(errors), result.get("feeds_processed", 0),
            [e.get("result", {}).get("message", "unknown") for e in errors],
        )
    else:
        logger.info(
            "parse_feeds_for_user(user=%d): %d feeds processed successfully",
            user_id, result.get("feeds_processed", 0),
        )
    return result


async def refresh_weekly_events(ctx):
    logger.info("Starting weekly events refresh...")
    redis = ctx["redis"]
    events = await asyncio.to_thread(compute_weekly_events)
    await set_cached_events(redis, events)

    # Build and store the reverse index for the recommendation engine
    reverse_index, summaries = build_reverse_index(events)
    set_cluster_index(reverse_index, summaries)

    logger.info(
        "Weekly events refresh complete: %d events, %d mapped articles",
        len(events), len(reverse_index),
    )
    return {"events_generated": len(events)}


# ── Worker lifecycle ───────────────────────────────────────────────────────────

def _wait_for_db_sync() -> None:
    """Blocking check that the DB and tables are ready."""
    import time
    for _ in range(10):
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM feeds LIMIT 1")
                cursor.close()
            return  # DB is ready
        except Exception:
            time.sleep(2)


async def startup(ctx):
    """Executed once when the worker starts."""
    # Wait for the API to create tables, running in a thread to avoid blocking
    await asyncio.to_thread(_wait_for_db_sync)

    await refresh_stale_feeds(ctx)
    await refresh_weekly_events(ctx)


# ── Worker settings ────────────────────────────────────────────────────────────

class WorkerSettings:
    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
    )
    on_startup = startup
    functions = [
        refresh_stale_feeds,
        refresh_weekly_events,
        refresh_all_publisher_freq,
        parse_feeds_for_user,
    ]
    cron_jobs = [
        cron(refresh_stale_feeds, hour=REFRESH_CRON_HOURS, minute=0),
        cron(refresh_weekly_events, hour=REFRESH_CRON_HOURS, minute=30),
        cron(refresh_all_publisher_freq, hour=3, minute=0),
    ]