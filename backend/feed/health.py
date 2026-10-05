"""
feed/health.py — feed-monitor overview and tag-coverage queries.

Status classification (derived, no stored state):
  dead     — consecutive_errors >= 8
  failing  — consecutive_errors >= 1
  silent   — fetch still works but the feed stopped publishing (last item is
             much older than the feed's own typical gap)
  unknown  — never fetched successfully or at all (brand new feed)
  ok       — everything else
"""

import json
import logging
from datetime import datetime, timezone

from database.init_db import get_db

logger = logging.getLogger(__name__)

_DEAD_THRESHOLD = 8
_SILENT_MIN_HOURS = 72.0  # never call it "silent" before 3 days without posts
_UNKNOWN_AFTER_DAYS = 14  # never-parsed feeds become "unknown" after 14 days


def _classify(row: dict) -> str:
    consecutive = int(row.get("consecutive_errors") or 0)
    if consecutive >= _DEAD_THRESHOLD:
        return "dead"
    if consecutive >= 1:
        return "failing"

    last_parsed = row.get("last_parsed_at")
    last_success = row.get("last_success_at")
    if not last_success and not last_parsed:
        error_at = row.get("last_error_at")
        if not error_at:
            return "unknown"

    gap = row.get("avg_gap_hours")
    last_item = row.get("last_item_at")
    if last_item and gap:
        try:
            age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(str(last_item)).replace(tzinfo=timezone.utc)).total_seconds() / 3600.0
            if age_h > max(_SILENT_MIN_HOURS, 2.5 * float(gap)):
                return "silent"
        except (ValueError, TypeError):
            pass
    return "ok"


def monitor_overview(user_id: int) -> dict:
    """All subscribed feeds + health columns + cached stats."""
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    f.feed_sha256,
                    f.feed_url AS url,
                    COALESCE(ufo.custom_title, f.feed_title) AS title,
                    f.feed_icon AS icon,
                    f.last_error, f.last_error_at,
                    f.consecutive_errors,
                    f.last_success_at, f.last_parsed_at,
                    f.last_http_status, f.last_fetch_ms,
                    f.entries_count,
                    fs.posts_4w, fs.posts_per_week,
                    fs.weekday_counts, fs.weekly_trend,
                    fs.avg_gap_hours, fs.last_item_at,
                    fs.classified_auto, fs.classified_manual, fs.classified_pct,
                    fs.weekday_tag_counts, fs.updated_at AS stats_updated_at
                FROM user_subscriptions us
                JOIN feeds f ON f.feed_sha256 = us.feed_sha256
                LEFT JOIN user_feed_overrides ufo
                    ON ufo.user_id = us.user_id AND ufo.feed_sha256 = f.feed_sha256
                LEFT JOIN feed_stats fs ON fs.feed_sha256 = f.feed_sha256
                WHERE us.user_id = %s
                ORDER BY COALESCE(ufo.custom_title, f.feed_title)
                """,
                (user_id,),
            )
            rows = cursor.fetchall()

            cursor.execute(
                "SELECT id, name, color FROM smart_tags WHERE user_id = %s",
                (user_id,),
            )
            user_tags = {int(t["id"]): t for t in cursor.fetchall()}
        finally:
            cursor.close()

    def _json(val):
        if val is None:
            return None
        if isinstance(val, (list, dict)):
            return val
        try:
            return json.loads(val)
        except (TypeError, ValueError):
            return None

    feeds = []
    for r in rows:
        stats = None
        if r.get("weekday_counts") is not None:
            weekday = _json(r["weekday_counts"]) or []
            trend = _json(r["weekly_trend"]) or []
            raw_tag_counts = _json(r["weekday_tag_counts"]) or {}

            by_tag = []
            for tid_str, counts in raw_tag_counts.items():
                try:
                    tid = int(tid_str)
                except (TypeError, ValueError):
                    continue
                meta = user_tags.get(tid)
                if not meta:
                    continue
                counts = (counts + [0] * 7)[:7]
                by_tag.append({
                    "tag_id": tid,
                    "name": meta["name"],
                    "color": meta["color"],
                    "counts": counts,
                    "total": sum(counts),
                })
            by_tag.sort(key=lambda x: x["total"], reverse=True)

            stats = {
                "posts_4w": r.get("posts_4w"),
                "posts_per_week": r.get("posts_per_week"),
                "weekday_counts": weekday,
                "weekday_by_tag": by_tag,
                "weekly_trend": trend,
                "avg_gap_hours": r.get("avg_gap_hours"),
                "last_item_at": r["last_item_at"].isoformat() if isinstance(r.get("last_item_at"), datetime) else r.get("last_item_at"),
                "classified_auto": r.get("classified_auto"),
                "classified_manual": r.get("classified_manual"),
                "classified_pct": r.get("classified_pct"),
                "updated_at": r["stats_updated_at"].isoformat() if isinstance(r.get("stats_updated_at"), datetime) else r.get("stats_updated_at"),
            }
        feeds.append({
            "feed_sha256": r["feed_sha256"],
            "url": r["url"],
            "title": r["title"],
            "icon": r["icon"],
            "status": _classify(r),
            "last_error": r.get("last_error"),
            "last_error_at": r["last_error_at"].isoformat() if isinstance(r.get("last_error_at"), datetime) else r.get("last_error_at"),
            "consecutive_errors": int(r.get("consecutive_errors") or 0),
            "last_success_at": r["last_success_at"].isoformat() if isinstance(r.get("last_success_at"), datetime) else r.get("last_success_at"),
            "last_parsed_at": r["last_parsed_at"].isoformat() if isinstance(r.get("last_parsed_at"), datetime) else r.get("last_parsed_at"),
            "last_http_status": r.get("last_http_status"),
            "last_fetch_ms": r.get("last_fetch_ms"),
            "entries_count": r.get("entries_count"),
            "stats": stats,
        })

    counts = {"ok": 0, "failing": 0, "dead": 0, "silent": 0, "unknown": 0}
    stale_stats = 0
    now = datetime.now(timezone.utc)
    for f in feeds:
        counts[f["status"]] += 1
        updated = (f.get("stats") or {}).get("updated_at")
        if not updated:
            stale_stats += 1
        else:
            try:
                age_h = (now - datetime.fromisoformat(updated)).total_seconds() / 3600.0
                if age_h > 24:
                    stale_stats += 1
            except (TypeError, ValueError):
                stale_stats += 1

    return {
        "feeds": feeds,
        "summary": counts,
        "has_smart_tags": bool(user_tags),
        "stale_stats": stale_stats,
    }


def tag_coverage(user_id: int) -> dict:
    """Per user tag: how many items are auto-classified vs manually tagged."""
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    st.id AS tag_id,
                    st.name, st.color,
                    SUM(at.source = 'manual') AS manual_count,
                    SUM(at.source <> 'manual') AS auto_count,
                    COUNT(at.id) AS total_count,
                    AVG(CASE WHEN at.source = 'ai' THEN at.confidence END) AS avg_confidence
                FROM smart_tags st
                LEFT JOIN article_tags at
                    ON at.tag_id = st.id AND at.user_id = st.user_id
                WHERE st.user_id = %s
                GROUP BY st.id, st.name, st.color
                ORDER BY auto_count DESC, st.name
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
        finally:
            cursor.close()

    tags = []
    for r in rows:
        manual = int(r.get("manual_count") or 0)
        auto = int(r.get("auto_count") or 0)
        total = int(r.get("total_count") or 0)
        tags.append({
            "tag_id": r["tag_id"],
            "name": r["name"],
            "color": r["color"],
            "manual_count": manual,
            "auto_count": auto,
            "total_count": total,
            "auto_pct": round(100.0 * auto / total, 1) if total else None,
            "avg_confidence": (
                round(float(r["avg_confidence"]) * 100.0, 1)
                if r.get("avg_confidence") is not None else None
            ),
        })

    return {"tags": tags}
