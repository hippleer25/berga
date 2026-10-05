"""
feed/stats.py — per-feed posting statistics computed from Qdrant + MySQL.

Computes, per feed_sha256:
  posts_4w            — article count in the last 28 days
  posts_per_week      — posts_4w / 4
  weekday_counts      — 7 ints (Monday-first), weekday distribution over the window
  weekly_trend        — 12 ints oldest→newest, one bucket per week
  avg_gap_hours       — mean gap between consecutive posts within the window
  last_item_at        — timestamp of the newest article
  classified_*        — distinct items in the window carrying smart-tag rows
                        (auto = feed/folder/regex/ai sources, manual = manual)
  weekday_tag_counts  — {tag_id: [7 ints]} — each item attributed to its primary
                        tag (manual > highest confidence > lowest id) so the
                        per-weekday tag stacks never double-count a post.

Results are cached in the `feed_stats` table and shown by /api/feed-monitor.
"""

import json
import logging
from datetime import datetime, timezone

from database.init_db import get_db
from intelligence.embeddings import get_qdrant_client, COLLECTION_NAME
from qdrant_client.http import models

logger = logging.getLogger(__name__)

TREND_WEEKS = 12
TREND_WINDOW_DAYS = TREND_WEEKS * 7
ITEM_CHUNK = 500
AUTO_SOURCES = ("feed", "folder", "regex", "ai")


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def _scroll_feed_item_ts(client, feed_sha256: str, min_ts: float) -> list[tuple[str, float]]:
    """Stream (item_id, pub_timestamp) for one feed inside the window."""
    out: list[tuple[str, float]] = []
    offset = None
    while True:
        kwargs: dict = {
            "collection_name": COLLECTION_NAME,
            "scroll_filter": models.Filter(
                must=[
                    models.FieldCondition(
                        key="feed_sha256",
                        match=models.MatchValue(value=feed_sha256),
                    ),
                    models.FieldCondition(
                        key="pub_timestamp",
                        range=models.Range(gte=min_ts),
                    ),
                ]
            ),
            "limit": 256,
            "with_payload": ["pub_timestamp"],
            "with_vectors": False,
        }
        if offset is not None:
            kwargs["offset"] = offset
        points, offset = client.scroll(**kwargs)
        for p in points:
            ts = (p.payload or {}).get("pub_timestamp")
            if isinstance(ts, (int, float)):
                out.append((str(p.id), float(ts)))
        if offset is None or not points:
            break
    return out


def _aggregate(item_ts: list[tuple[str, float]], now: float):
    """Derive counts/trend/histogram from the window's (id, ts) pairs."""
    item_ts.sort(key=lambda x: x[1])
    tss = [ts for _, ts in item_ts]

    posts_4w = sum(1 for ts in tss if ts >= now - 28 * 86400)
    posts_per_week = posts_4w / 4.0

    # Week buckets are anchored to `now` (bucket 11 = current week).
    weekly_trend = [0] * TREND_WEEKS
    weekday_counts = [0] * 7
    item_weekday: dict[str, int] = {}
    for item_id, ts in item_ts:
        weeks_ago = int((now - ts) // (7 * 86400))
        if 0 <= weeks_ago < TREND_WEEKS:
            weekly_trend[TREND_WEEKS - 1 - weeks_ago] += 1
        try:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            wd = dt.weekday()
            weekday_counts[wd] += 1
            item_weekday[item_id] = wd
        except (OverflowError, OSError, ValueError):
            pass

    avg_gap_hours = None
    if len(tss) > 1:
        avg_gap_hours = round((tss[-1] - tss[0]) / (len(tss) - 1) / 3600.0, 1)

    last_item_at = None
    if tss:
        last_item_at = datetime.fromtimestamp(tss[-1], tz=timezone.utc).replace(tzinfo=None)

    return {
        "posts_4w": posts_4w,
        "posts_per_week": round(posts_per_week, 2),
        "weekday_counts": weekday_counts,
        "weekly_trend": weekly_trend,
        "avg_gap_hours": avg_gap_hours,
        "last_item_at": last_item_at.isoformat(sep=" ") if last_item_at else None,
        "item_weekday": item_weekday,
    }


def _tag_stats(item_weekday: dict[str, int]):
    """
    Returns (auto_items, manual_items, weekday_tag_counts).

    weekday_tag_counts maps tag_id -> [7] using each item's *primary* tag so a
    post carrying several tags is counted once per weekday stack.
    """
    if not item_weekday:
        return 0, 0, {}

    auto_items: set[str] = set()
    manual_items: set[str] = set()
    primary: dict[str, tuple] = {}  # item_id -> (sort_key, tag_id)
    ids = list(item_weekday.keys())

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                for start in range(0, len(ids), ITEM_CHUNK):
                    chunk = ids[start:start + ITEM_CHUNK]
                    placeholders = ",".join(["%s"] * len(chunk))
                    cursor.execute(
                        f"""
                        SELECT item_id, tag_id, source, confidence
                        FROM article_tags
                        WHERE item_id IN ({placeholders})
                        """,
                        chunk,
                    )
                    for item_id, tag_id, source, confidence in cursor.fetchall():
                        item_id = str(item_id)
                        tag_id = int(tag_id)
                        if source in AUTO_SOURCES:
                            auto_items.add(item_id)
                        elif source == "manual":
                            manual_items.add(item_id)
                        # manual wins, then highest confidence, then lowest id
                        rank = (0 if source == "manual" else 1,
                                -(float(confidence) if confidence is not None else 0.0),
                                tag_id)
                        cur = primary.get(item_id)
                        if cur is None or rank < cur[0]:
                            primary[item_id] = (rank, tag_id)
            finally:
                cursor.close()
    except Exception:
        logger.warning("Could not compute tag stats", exc_info=True)

    weekday_tag: dict[str, list[int]] = {}
    for item_id, (_, tag_id) in primary.items():
        wd = item_weekday.get(item_id)
        if wd is None:
            continue
        weekday_tag.setdefault(str(tag_id), [0] * 7)[wd] += 1

    return len(auto_items), len(manual_items), weekday_tag


def _upsert_feed_stats(sha: str, agg: dict, auto_c: int, manual_c: int,
                       weekday_tag: dict) -> None:
    denom = agg["posts_4w"]
    pct = round(100.0 * (auto_c + manual_c) / denom, 1) if denom else None
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO feed_stats
                    (feed_sha256, posts_4w, posts_per_week, weekday_counts,
                     weekly_trend, avg_gap_hours, last_item_at,
                     classified_auto, classified_manual, classified_pct,
                     weekday_tag_counts)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    posts_4w = VALUES(posts_4w),
                    posts_per_week = VALUES(posts_per_week),
                    weekday_counts = VALUES(weekday_counts),
                    weekly_trend = VALUES(weekly_trend),
                    avg_gap_hours = VALUES(avg_gap_hours),
                    last_item_at = VALUES(last_item_at),
                    classified_auto = VALUES(classified_auto),
                    classified_manual = VALUES(classified_manual),
                    classified_pct = VALUES(classified_pct),
                    weekday_tag_counts = VALUES(weekday_tag_counts)
                """,
                (
                    sha,
                    agg["posts_4w"],
                    agg["posts_per_week"],
                    json.dumps(agg["weekday_counts"]),
                    json.dumps(agg["weekly_trend"]),
                    agg["avg_gap_hours"],
                    agg["last_item_at"],
                    auto_c,
                    manual_c,
                    pct,
                    json.dumps(weekday_tag),
                ),
            )
            conn.commit()
        finally:
            cursor.close()


def compute_feed_stats(feed_hashes: list[str]) -> dict[str, dict]:
    """
    Compute + persist stats for the given feeds (chunks the corpus to bound
    Qdrant load). Returns {feed_sha256: stats_dict} for the successful ones.
    """
    if not feed_hashes:
        return {}

    now = _now_ts()
    min_ts = now - TREND_WINDOW_DAYS * 86400
    client = get_qdrant_client()
    results: dict[str, dict] = {}

    for sha in feed_hashes:
        try:
            item_ts = _scroll_feed_item_ts(client, sha, min_ts)
            agg = _aggregate(item_ts, now)
            auto_c, manual_c, weekday_tag = _tag_stats(agg.pop("item_weekday"))
            agg["classified_auto"] = auto_c
            agg["classified_manual"] = manual_c
            agg["classified_pct"] = (
                round(100.0 * (auto_c + manual_c) / agg["posts_4w"], 1) if agg["posts_4w"] else None
            )
            _upsert_feed_stats(sha, agg, auto_c, manual_c, weekday_tag)
            results[sha] = agg
        except Exception as exc:
            logger.warning("Feed stats failed for %s: %s", sha[:8], exc)

    return results
