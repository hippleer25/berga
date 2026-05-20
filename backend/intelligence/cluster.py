"""
intelligence/cluster.py — Event clustering from RSS feeds.

Groups similar articles from the last N days using DBSCAN,
then generates a summary headline for each cluster using an LLM.
"""

import json
import numpy as np
import logging
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from sklearn.cluster import DBSCAN
from intelligence.embeddings import get_qdrant_client, COLLECTION_NAME
from mota.ai_lib import generate_text
from database.init_db import get_db
from qdrant_client.http import models
import os

logger = logging.getLogger(__name__)

CACHE_KEY = os.getenv("CACHE_KEY", "weekly_events_cache")
CACHE_TTL = int(os.getenv("CACHE_TTL", 60 * 60 * 6))
CACHE_FRESHNESS_SECONDS = int(os.getenv("CACHE_FRESHNESS_SECONDS", 60 * 30))

CLUSTER_EPS = float(os.getenv("CLUSTER_EPS", "0.2"))
MAX_CLUSTER_FRACTION = float(os.getenv("MAX_CLUSTER_FRACTION", "0.25"))
SCROLL_PAGE_SIZE = 500


# ------------------------------------------------------------------
# Cache Redis
# ------------------------------------------------------------------

async def get_cached_events(redis) -> list[dict] | None:
    data = await redis.get(CACHE_KEY)
    if not data:
        logger.info("[CLUSTER] Cache miss — no events in cache")
        return None

    parsed = json.loads(data)

    if isinstance(parsed, list):
        logger.warning("[CLUSTER] Cache in legacy format (no timestamp) — ignoring and regenerating")
        return None

    cached_at_str = parsed.get("cached_at")
    if not cached_at_str:
        logger.warning("[CLUSTER] Cache missing timestamp — ignoring and regenerating")
        return None

    cached_at = datetime.fromisoformat(cached_at_str)
    age_seconds = (datetime.now(timezone.utc) - cached_at).total_seconds()

    if age_seconds > CACHE_FRESHNESS_SECONDS:
        logger.info(
            f"[CLUSTER] Cache expired — generated {age_seconds / 60:.1f} min ago "
            f"(limit: {CACHE_FRESHNESS_SECONDS / 60:.0f} min) — regenerating"
        )
        return None

    events = parsed.get("events", [])
    logger.info(
        f"[CLUSTER] Cache hit — {len(events)} events in Redis "
        f"(generated {age_seconds / 60:.1f} min ago)"
    )
    return events


async def set_cached_events(redis, events: list[dict]):
    payload = {
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "events": events,
    }
    await redis.set(CACHE_KEY, json.dumps(payload, ensure_ascii=False), ex=CACHE_TTL)
    logger.info(f"[CLUSTER] Cache saved — {len(events)} events (TTL: 6h, freshness: 30min)")


# ------------------------------------------------------------------
# Qdrant
# ------------------------------------------------------------------

def _fetch_week_vectors(days: int = 7) -> tuple[np.ndarray, list[dict]]:
    client = get_qdrant_client()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
    since_dt = datetime.fromtimestamp(since, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

    logger.info(f"[CLUSTER] Fetching articles since {since_dt} (last {days} days)")

    scroll_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="pub_timestamp",
                range=models.Range(gte=since)
            )
        ]
    )

    all_points = []
    offset = None
    while True:
        points, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=scroll_filter,
            with_vectors=True,
            with_payload=True,
            limit=SCROLL_PAGE_SIZE,
            offset=offset,
        )
        all_points.extend(points)
        if next_offset is None:
            break
        offset = next_offset

    if not all_points:
        logger.warning("[CLUSTER] No articles found in Qdrant for the period")
        return np.array([]), []

    vectors = np.array([p.vector for p in all_points], dtype=np.float32)
    payloads = [{**p.payload, "_point_id": str(p.id)} for p in all_points]

    logger.info(f"[CLUSTER] {len(all_points)} articles loaded — vectors shape: {vectors.shape}")
    return vectors, payloads


# ------------------------------------------------------------------
# Feed enrichment
# ------------------------------------------------------------------

def _enrich_with_feed_metadata(articles: list[dict]) -> list[dict]:
    """Fetch feed_title, feed_icon, and feed_link from MySQL and enrich articles."""
    feed_hashes = list(set(
        a.get("feed_sha256") for a in articles if a.get("feed_sha256")
    ))

    if not feed_hashes:
        return articles

    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                fmt = ",".join(["%s"] * len(feed_hashes))
                cursor.execute(
                    f"SELECT feed_sha256, feed_title, feed_icon, feed_link "
                    f"FROM feeds WHERE feed_sha256 IN ({fmt})",
                    tuple(feed_hashes),
                )
                feeds_info = {row["feed_sha256"]: row for row in cursor.fetchall()}
                logger.info(f"[CLUSTER] Feed metadata loaded for {len(feeds_info)} unique feeds")
            finally:
                cursor.close()
    except Exception as e:
        logger.error(f"[CLUSTER] Error fetching feed metadata: {e}")
        feeds_info = {}

    for article in articles:
        f_hash = article.get("feed_sha256")
        if f_hash and f_hash in feeds_info:
            article["feed_title"] = feeds_info[f_hash]["feed_title"]
            article["feed_icon"] = feeds_info[f_hash]["feed_icon"]
            article["feed_link"] = feeds_info[f_hash]["feed_link"]

    return articles


# ------------------------------------------------------------------
# Clustering
# ------------------------------------------------------------------

def _count_unique_feeds(articles: list[dict]) -> int:
    return len(set(a.get("feed_sha256") for a in articles if a.get("feed_sha256")))


def _run_clustering(vectors: np.ndarray, min_cluster_size: int) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    normalized = vectors / np.where(norms == 0, 1, norms)

    logger.info(
        f"[CLUSTER] Using fixed eps={CLUSTER_EPS:.4f} "
        f"(min_samples={min_cluster_size})"
    )

    clusterer = DBSCAN(
        eps=CLUSTER_EPS,
        min_samples=min_cluster_size,
        metric="euclidean",
        n_jobs=2,
    )
    labels = clusterer.fit_predict(normalized)

    n_clusters = len(set(labels) - {-1})
    n_noise = int(np.sum(labels == -1))

    logger.info(
        f"[CLUSTER] Result: {n_clusters} clusters found, "
        f"{n_noise} articles discarded as noise ({n_noise / len(vectors) * 100:.1f}%)"
    )

    if n_clusters == 0:
        logger.warning("[CLUSTER] No clusters formed — consider increasing eps or reducing min_samples")

    return labels


def _summarize_cluster(articles: list[dict]) -> str:
    titles = [a.get("title", "") for a in articles[:10] if a.get("title")]
    titles_text = "\n".join(f"- {t}" for t in titles)

    logger.debug(f"[CLUSTER] Generating summary for cluster with {len(articles)} articles")

    prompt = (
        "You are a newspaper editor. "
        "The headlines below cover the same event from this week. "
        "Write ONE direct sentence in a journalistic headline style, "
        "without quotation marks, maximum 20 words, in the language with most posts, "
        "Do not use any markup or HTML tags. "
        "Regardless of the original language of the headlines:\n\n"
        f"{titles_text}\n\nHeadline:"
    )

    result = generate_text(prompt, usage="cluster")

    if result:
        logger.info(f"[CLUSTER] Summary generated: \"{result}\"")
    else:
        fallback = titles[0] if titles else "Untitled event"
        logger.warning(f"[CLUSTER] LLM failed — using fallback: \"{fallback}\"")

    return result if result else (titles[0] if titles else "Untitled event")


def _build_events(valid_clusters: list[list[dict]]) -> list[dict]:
    logger.info(f"[CLUSTER] Generating summaries for {len(valid_clusters)} clusters in parallel...")

    all_articles = [a for cluster in valid_clusters for a in cluster]
    _enrich_with_feed_metadata(all_articles)

    with ThreadPoolExecutor(max_workers=min(5, len(valid_clusters))) as executor:
        summaries = list(executor.map(_summarize_cluster, valid_clusters))

    return [
        {
            "article_count": len(articles),
            "unique_feeds": _count_unique_feeds(articles),
            "summary": summary.replace("*", ""),
            "articles": [
                {
                    "item_id": a.get("_point_id"),
                    "title": a.get("title"),
                    "url": a.get("link"),
                    "source": a.get("feed_title"),
                    "feed_icon": a.get("feed_icon"),
                    "published_at": a.get("pub_date"),
                }
                for a in articles
            ]
        }
        for articles, summary in zip(valid_clusters, summaries)
    ]


def compute_weekly_events(
    min_cluster_size: int = 3,
    min_unique_feeds: int = 2,
    days: int = 7,
    limit: int = 100,
) -> list[dict]:
    logger.info(
        f"[CLUSTER] Starting pipeline — days={days}, "
        f"min_cluster_size={min_cluster_size}, min_unique_feeds={min_unique_feeds}, limit={limit}"
    )

    vectors, payloads = _fetch_week_vectors(days=days)

    if len(vectors) < min_cluster_size:
        logger.warning(
            f"[CLUSTER] Only {len(vectors)} articles — minimum required: {min_cluster_size}. Aborting."
        )
        return []

    labels = _run_clustering(vectors, min_cluster_size)

    clusters: dict[int, list] = defaultdict(list)
    for label, payload in zip(labels, payloads):
        if label != -1:
            clusters[label].append(payload)

    total_articles = len(vectors)
    max_cluster_size = int(total_articles * MAX_CLUSTER_FRACTION)

    for cid, arts in sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True):
        unique_feeds = _count_unique_feeds(arts)
        if len(arts) > max_cluster_size:
            logger.warning(
                f"[CLUSTER] Cluster {cid} discarded — {len(arts)} articles "
                f"exceeds {MAX_CLUSTER_FRACTION:.0%} of total ({max_cluster_size}). "
                f"Likely a mega-cluster."
            )
            del clusters[cid]
            continue
        logger.info(
            f"[CLUSTER] Cluster {cid}: {len(arts)} articles, {unique_feeds} unique feeds "
            f"— e.g.: \"{arts[0].get('title', 'no title')}\""
        )

    valid = sorted(
        [
            v for v in clusters.values()
            if len(v) >= min_cluster_size and _count_unique_feeds(v) >= min_unique_feeds
        ],
        key=len,
        reverse=True
    )[:limit]

    logger.info(
        f"[CLUSTER] {len(valid)} valid clusters "
        f"(>= {min_cluster_size} articles and >= {min_unique_feeds} unique feeds) after filter"
    )

    if not valid:
        logger.warning(
            "[CLUSTER] No clusters passed the filter — try reducing min_cluster_size or min_unique_feeds"
        )
        return []

    events = _build_events(valid)
    logger.info(f"[CLUSTER] Pipeline complete — {len(events)} events generated")
    return events