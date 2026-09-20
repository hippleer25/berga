"""
intelligence/cluster.py — Event clustering from RSS feeds.

Groups similar articles from the last N days using DBSCAN with
adaptive eps (auto-tuned from k-NN distance distribution), then
generates a summary headline for each cluster using an LLM.

Events are persisted to MySQL so they survive restarts. Clusters
that already exist in the DB reuse their LLM-generated summary,
avoiding redundant (and expensive) LLM calls on every cycle.
"""

import hashlib
import json
import numpy as np
import logging
from datetime import datetime, timedelta, timezone
from collections import defaultdict


from intelligence.embeddings import get_qdrant_client, COLLECTION_NAME
from mota.ai_lib import generate_text
from database.init_db import get_db
from qdrant_client.http import models
import os

logger = logging.getLogger(__name__)

CACHE_KEY = os.getenv("CACHE_KEY", "weekly_events_cache")
CACHE_TTL = int(os.getenv("CACHE_TTL", 60 * 60 * 6))
CACHE_FRESHNESS_SECONDS = int(os.getenv("CACHE_FRESHNESS_SECONDS", 60 * 30))

CLUSTER_EPS_OVERRIDE = os.getenv("CLUSTER_EPS") or None
CLUSTER_EPS_PERCENTILE = int(os.getenv("CLUSTER_EPS_PERCENTILE", "15"))
CLUSTER_EPS_MAX = float(os.getenv("CLUSTER_EPS_MAX", "0.35"))
CLUSTER_MIN_CLUSTER_SIZE = int(os.getenv("CLUSTER_MIN_CLUSTER_SIZE", "3"))
CLUSTER_MIN_UNIQUE_FEEDS = int(os.getenv("CLUSTER_MIN_UNIQUE_FEEDS", "2"))
CLUSTER_DAYS = int(os.getenv("CLUSTER_DAYS", "7"))
CLUSTER_LIMIT = int(os.getenv("CLUSTER_LIMIT", "100"))
SCROLL_PAGE_SIZE = 500
MAX_ARTICLES = 5000


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
    logger.info(
        f"[CLUSTER] Cache saved — {len(events)} events "
        f"(TTL: {CACHE_TTL // 60}min, freshness: {CACHE_FRESHNESS_SECONDS // 60}min)"
    )


# ------------------------------------------------------------------
# MySQL persistence
# ------------------------------------------------------------------

def compute_cluster_hash(article_ids: list[str]) -> str:
    sorted_ids = sorted(set(article_ids))
    raw = "|".join(sorted_ids)
    return hashlib.sha256(raw.encode()).hexdigest()


def load_events_from_db() -> list[dict] | None:
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(
                    "SELECT cluster_hash, summary, article_count, unique_feeds, articles_json "
                    "FROM weekly_events ORDER BY article_count DESC"
                )
                rows = cursor.fetchall()
            finally:
                cursor.close()
    except Exception as e:
        logger.error(f"[CLUSTER] Error loading events from DB: {e}")
        return None

    if not rows:
        logger.info("[CLUSTER] No events found in DB")
        return None

    events = []
    for row in rows:
        try:
            articles = json.loads(row["articles_json"])
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "[CLUSTER] Skipping DB event with hash=%s — invalid articles_json",
                row["cluster_hash"][:12],
            )
            continue
        events.append({
            "cluster_hash": row["cluster_hash"],
            "summary": row["summary"],
            "article_count": row["article_count"],
            "unique_feeds": row["unique_feeds"],
            "articles": articles,
        })

    logger.info(f"[CLUSTER] Loaded {len(events)} events from DB")
    return events


def _persist_events_to_db(events: list[dict], active_cluster_hashes: set[str]) -> None:
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                for event in events:
                    ch = event.get("cluster_hash")
                    if not ch:
                        continue
                    articles_json = json.dumps(
                        event.get("articles", []), ensure_ascii=False
                    )
                    cursor.execute(
                        "INSERT INTO weekly_events "
                        "(cluster_hash, summary, article_count, unique_feeds, articles_json) "
                        "VALUES (%s, %s, %s, %s, %s) "
                        "ON DUPLICATE KEY UPDATE "
                        "summary = VALUES(summary), "
                        "article_count = VALUES(article_count), "
                        "unique_feeds = VALUES(unique_feeds), "
                        "articles_json = VALUES(articles_json)",
                        (
                            ch,
                            event["summary"],
                            event["article_count"],
                            event["unique_feeds"],
                            articles_json,
                        ),
                    )
                if active_cluster_hashes:
                    fmt = ",".join(["%s"] * len(active_cluster_hashes))
                    cursor.execute(
                        f"DELETE FROM weekly_events WHERE cluster_hash NOT IN ({fmt})",
                        tuple(active_cluster_hashes),
                    )
                    deleted = cursor.rowcount
                else:
                    cursor.execute("DELETE FROM weekly_events")
                    deleted = cursor.rowcount
                if deleted:
                    logger.info(f"[CLUSTER] Deleted {deleted} stale events from DB")
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"[CLUSTER] Error persisting events to DB: {e}")
                raise
            finally:
                cursor.close()
    except Exception as e:
        logger.error(f"[CLUSTER] Error in _persist_events_to_db: {e}")


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
        if len(all_points) >= MAX_ARTICLES:
            logger.warning(
                f"[CLUSTER] Reached {MAX_ARTICLES} article cap — truncating. "
                f"More articles exist in the window but will be skipped."
            )
            break

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


def _pairwise_cosine_dist(normalized: np.ndarray, block: int = 512) -> np.ndarray:
    """
    Cosine distance matrix (1 − X·Yᵀ) computed in blocks so the fp32
    transient stays small. Self-distance is set to exactly 0 afterwards,
    matching sklearn's handling of the diagonal.
    """
    n = normalized.shape[0]
    x = normalized.astype(np.float32, copy=False)
    d = np.empty((n, n), dtype=np.float32)
    for i in range(0, n, block):
        j_end = min(i + block, n)
        chunk = x[i:j_end] @ x.T          # cosine similarity
        np.clip(chunk, -1.0, 1.0, out=chunk)
        chunk *= -1.0                     # → -cos
        chunk += 1.0                      # → cosine distance
        d[i:j_end] = chunk
    np.fill_diagonal(d, 0.0)
    return d


def _kth_distance(dists: np.ndarray, k: int) -> np.ndarray:
    """Kth nearest-neighbour distance per row (k includes the point itself)."""
    part = np.partition(dists, kth=k - 1, axis=1)
    return part[:, k - 1]


def _compute_adaptive_eps(normalized: np.ndarray, k: int) -> float:
    n_samples = normalized.shape[0]
    effective_k = min(k, n_samples - 1) if n_samples > 1 else 1

    dists = _pairwise_cosine_dist(normalized)
    kth_distances = np.sort(_kth_distance(dists, effective_k))

    eps = float(np.percentile(kth_distances, CLUSTER_EPS_PERCENTILE))
    eps = min(eps, CLUSTER_EPS_MAX)

    logger.info(
        f"[CLUSTER] Adaptive eps from k-NN (k={effective_k}, p={CLUSTER_EPS_PERCENTILE}, metric=cosine): "
        f"eps={eps:.4f} (capped at {CLUSTER_EPS_MAX:.2f}) "
        f"(p2={np.percentile(kth_distances, 2):.4f}, "
        f"p10={np.percentile(kth_distances, 10):.4f}, "
        f"p50={np.percentile(kth_distances, 50):.4f}, "
        f"p90={np.percentile(kth_distances, 90):.4f})"
    )
    return eps


# ------------------------------------------------------------------
# Density clustering (pure-numpy DBSCAN equivalent)
# ------------------------------------------------------------------
# Faithful to sklearn.cluster.DBSCAN semantics:
#   – neighbours = points with cosine distance ≤ eps (self counts)
#   – core points: ≥ min_samples neighbours
#   – clusters grow by BFS through core points; border points join the
#     first point's cluster that reaches them
#   – points not reachable from any core point are noise (-1)

def _numpy_dbscan(dists: np.ndarray, eps: float, min_samples: int) -> np.ndarray:
    n = dists.shape[0]
    labels = np.full(n, -1, dtype=np.int64)
    if n == 0:
        return labels

    neighbours = dists <= eps          # boolean adjacency (self included, d=0 ≤ eps)
    is_core = neighbours.sum(axis=1) >= min_samples

    visited = np.zeros(n, dtype=bool)
    cluster_id = 0

    for p in range(n):
        if visited[p]:
            continue
        if not is_core[p]:
            # Border or noise point: leave unassigned for now; a core
            # point expanding a cluster may still claim it.
            visited[p] = True
            continue

        # ── Expand a new cluster: BFS over directly-reachable points ──
        # Seed with p's own neighbourhood; every newly found core point
        # contributes its neighbourhood to the expansion.
        seeds = np.flatnonzero(neighbours[p]).tolist()
        for q in seeds:
            labels[q] = cluster_id
            visited[q] = True
        queue = seeds if is_core[p] else []
        while queue:
            q = queue.pop(0)
            if not is_core[q]:
                continue
            # Neighbours of q not claimed by any earlier cluster join here.
            for r in np.flatnonzero(neighbours[q]):
                r = int(r)
                if visited[r]:
                    continue
                visited[r] = True
                labels[r] = cluster_id
                queue.append(r)
            is_core[q] = False  # mark core as fully expanded
        cluster_id += 1

    return labels


def _run_clustering(vectors: np.ndarray, min_cluster_size: int) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    normalized = vectors / np.where(norms == 0, 1, norms)

    dbscan_min_samples = max(min_cluster_size, 3)

    if CLUSTER_EPS_OVERRIDE is not None:
        eps = float(CLUSTER_EPS_OVERRIDE)
        logger.info(
            f"[CLUSTER] Using overridden eps={eps:.4f} "
            f"(min_samples={dbscan_min_samples}, metric=cosine)"
        )
    else:
        eps = _compute_adaptive_eps(normalized, dbscan_min_samples)

    dists = _pairwise_cosine_dist(normalized)
    labels = _numpy_dbscan(dists, eps, dbscan_min_samples)

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
        "The headlines below cover the same event from this week.\n\n"
        "Task: write ONE new headline that synthesizes the shared event across ALL of them.\n"
        "Rules:\n"
        "- NEVER copy any single headline (or any part of one) verbatim — always synthesize.\n"
        "- Merge the common facts; drop outlet-specific details.\n"
        "- Direct sentence, journalistic headline style, no quotation marks.\n"
        "- Maximum 20 words.\n"
        "- Write in the language used by most headlines.\n"
        "- Do not use any markup, HTML tags, or list formatting.\n\n"
        f"{titles_text}\n\nSynthesized headline:"
    )

    result = generate_text(prompt, usage="summarize", max_tokens=256, max_retries=5)

    if result:
        logger.info(f"[CLUSTER] Summary generated: \"{result}\"")
    else:
        logger.warning(
            "[CLUSTER] LLM headline generation failed (returned empty/None after "
            "retries) — falling back to first member title"
        )
        result = _fallback_title(articles)

    return result


# Force regeneration of stored summaries on next run (one-shot escape hatch).
CLUSTER_REGENERATE_SUMMARIES = os.getenv("CLUSTER_REGENERATE_SUMMARIES", "0") == "1"


def _summary_is_stale(summary: str, articles: list[dict]) -> bool:
    """True when the stored summary is just a copy of a member title (or
    a generic placeholder) — i.e. a previous fallback, not a real synthesis."""
    if not summary:
        return True
    s = summary.strip().lower()
    if s in ("untitled event", "no title"):
        return True
    for a in articles:
        t = (a.get("title") or "").strip().lower()
        if t and t == s:
            return True
    return False


def _fallback_title(articles: list[dict]) -> str:
    titles = [a.get("title", "") for a in articles[:10] if a.get("title")]
    return titles[0] if titles else "Untitled event"


def _build_events(
    valid_clusters: list[list[dict]],
    existing_db_events: dict[str, str] | None = None,
) -> list[dict]:
    logger.info(f"[CLUSTER] Generating summaries for {len(valid_clusters)} clusters...")

    all_articles = [a for cluster in valid_clusters for a in cluster]
    _enrich_with_feed_metadata(all_articles)

    existing = existing_db_events or {}

    cluster_hashes: list[str] = []
    for cluster in valid_clusters:
        ids = [a.get("_point_id") for a in cluster if a.get("_point_id")]
        cluster_hashes.append(compute_cluster_hash(ids))

    skipped_llm = 0
    summaries: list[str | None] = [None] * len(valid_clusters)

    for i, (cluster, ch) in enumerate(zip(valid_clusters, cluster_hashes)):
        stored = existing.get(ch)
        if stored and not CLUSTER_REGENERATE_SUMMARIES and not _summary_is_stale(stored, cluster):
            summaries[i] = stored
            skipped_llm += 1
            logger.debug(
                f"[CLUSTER] Cluster {i}: reusing DB summary for hash={ch[:12]}"
            )
        else:
            if stored and _summary_is_stale(stored, cluster):
                logger.info(
                    f"[CLUSTER] Cluster {i}: stale summary for hash={ch[:12]} "
                    f"(copies a member title or placeholder) — regenerating"
                )
            try:
                summaries[i] = _summarize_cluster(cluster)
            except Exception as e:
                logger.warning(
                    f"[CLUSTER] Cluster {i} summary failed: {e} — using fallback title"
                )
                summaries[i] = None

    for i, s in enumerate(summaries):
        if s is None:
            summaries[i] = _fallback_title(valid_clusters[i])

    if skipped_llm:
        logger.info(
            f"[CLUSTER] Reused {skipped_llm}/{len(valid_clusters)} summaries from DB "
            f"— saved {skipped_llm} LLM calls"
        )

    events = []
    for articles, summary, ch in zip(valid_clusters, summaries, cluster_hashes):
        events.append({
            "cluster_hash": ch,
            "article_count": len(articles),
            "unique_feeds": _count_unique_feeds(articles),
            "summary": summary.replace("*", ""),
            "articles": [
                {
                    "item_id": a.get("_point_id"),
                    "title": a.get("title"),
                    "url": a.get("link"),
                    "source": a.get("feed_title"),
                    "feed_sha256": a.get("feed_sha256"),
                    "feed_icon": a.get("feed_icon"),
                    "published_at": a.get("pub_date"),
                }
                for a in articles
            ],
        })

    return events


def compute_weekly_events(
    min_cluster_size: int = CLUSTER_MIN_CLUSTER_SIZE,
    min_unique_feeds: int = CLUSTER_MIN_UNIQUE_FEEDS,
    days: int = CLUSTER_DAYS,
    limit: int = CLUSTER_LIMIT,
) -> list[dict]:
    logger.info(
        f"[CLUSTER] Starting pipeline — days={days}, "
        f"min_cluster_size={min_cluster_size}, min_unique_feeds={min_unique_feeds}, limit={limit}"
    )

    existing_db_events = load_events_from_db()
    existing_hash_to_summary: dict[str, str] = {}
    if existing_db_events:
        for ev in existing_db_events:
            ch = ev.get("cluster_hash")
            if ch:
                existing_hash_to_summary[ch] = ev["summary"]
        logger.info(
            f"[CLUSTER] Found {len(existing_hash_to_summary)} existing event summaries in DB"
        )

    vectors, payloads = _fetch_week_vectors(days=days)

    if len(vectors) < min_cluster_size:
        logger.warning(
            f"[CLUSTER] Only {len(vectors)} articles — minimum required: {min_cluster_size}. Aborting."
        )
        if existing_db_events:
            logger.info("[CLUSTER] Returning stale DB events as fallback")
            for ev in existing_db_events:
                ev.pop("cluster_hash", None)
            return existing_db_events
        return []

    labels = _run_clustering(vectors, min_cluster_size)

    clusters: dict[int, list] = defaultdict(list)
    for label, payload in zip(labels, payloads):
        if label != -1:
            clusters[label].append(payload)

    for cid, arts in sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True):
        unique_feeds = _count_unique_feeds(arts)
        logger.info(
            f"[CLUSTER] Cluster {cid}: {len(arts)} articles, {unique_feeds} unique feeds "
            f"— e.g.: \"{arts[0].get('title', 'no title')}\""
        )

    total_raw = len(clusters)
    passed_size = [v for v in clusters.values() if len(v) >= min_cluster_size]
    passed_feeds = [v for v in passed_size if _count_unique_feeds(v) >= min_unique_feeds]
    valid = sorted(passed_feeds, key=len, reverse=True)[:limit]

    logger.info(
        f"[CLUSTER] {total_raw} raw DBSCAN clusters → "
        f"{len(passed_size)} passed size filter (≥{min_cluster_size}) → "
        f"{len(passed_feeds)} passed feed filter (≥{min_unique_feeds} feeds) → "
        f"{len(valid)} kept (limit={limit})"
    )

    if not valid:
        logger.warning(
            "[CLUSTER] No clusters passed the filter — try reducing min_cluster_size or min_unique_feeds"
        )
        if existing_db_events:
            logger.info("[CLUSTER] Returning stale DB events as fallback")
            for ev in existing_db_events:
                ev.pop("cluster_hash", None)
            return existing_db_events
        return []

    events = _build_events(valid, existing_db_events=existing_hash_to_summary)

    active_hashes = set()
    for ev in events:
        ch = ev.get("cluster_hash")
        if ch:
            active_hashes.add(ch)

    _persist_events_to_db(events, active_hashes)

    for ev in events:
        ev.pop("cluster_hash", None)

    logger.info(f"[CLUSTER] Pipeline complete — {len(events)} events generated")
    return events
