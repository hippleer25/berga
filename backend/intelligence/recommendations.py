"""
intelligence/recommendations.py — Intelligent RSS feed ranking engine.

Three-tier recommendation system:
  Tier 1:   Personalised  — user has interaction vectors
  Tier 1.5: Cold-start    — user has no vectors; popularity + recency
  Tier 2:   Chronological — fallback when Tier 1/1.5 is exhausted

Memory optimisations applied in this version
─────────────────────────────────────────────
1. Slim cache entries
   Only the fields actually consumed by the frontend are stored in the
   ranking cache. Payload fields are explicitly allowlisted via
   _PAYLOAD_FIELDS. This prevents surprise large fields from inflating
   RAM over time and makes the cache footprint predictable.

   Known Qdrant payload fields:
     title, description, author, link, pub_date, pub_timestamp,
     feed_sha256, feed_title, feed_icon, url_hash

   feed_title and feed_icon already live in the Qdrant payload, so the
   per-page MySQL enrichment query has been removed. If a cached item is
   missing either field (legacy data), a single batched DB lookup fills
   the gap for just that page.

2. Smaller pre-compute window
   COMPUTE_N_RESULTS default lowered from 500 → 200. For a single-user
   deployment the saving is immediate; for multi-user it reduces per-entry
   cache size while still covering many pages of infinite scroll.

3. Smaller cache ceiling
   RANKING_CACHE_MAX_ENTRIES default lowered from 500 → 50. 50 unique
   (user, max_days, feed_filter) combinations resident at a time is
   generous for most deployments.

Score normalisation and global list guarantees are unchanged — relevance_score
always matches display order and continues across pages without resetting.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

from database.init_db import get_db
from intelligence.embeddings import get_qdrant_client, COLLECTION_NAME
from intelligence.scoring_util import (
    article_popularity,
    blend_vectors,
    contrast_score,
    publisher_engagement,
    publisher_frequency_bonus,
    time_decay_multiplier,
)
from intelligence.cluster_store import get_cluster_index, get_cluster_summaries
from qdrant_client.http import models

logger = logging.getLogger(__name__)

# ── Scoring constants ──────────────────────────────────────────────────────────

CONTRAST_EXPONENT   = float(os.getenv("CONTRAST_EXPONENT",   0.65))
ENGAGEMENT_EXPONENT = float(os.getenv("ENGAGEMENT_EXPONENT", 1.1))
FREQ_EXPONENT       = float(os.getenv("FREQ_EXPONENT",       0.5))
FREQ_BONUS_CAP      = float(os.getenv("FREQ_BONUS_CAP",      3.0))
FREQ_REF_DAYS       = float(os.getenv("FREQ_REF_DAYS",       30.0))
TIME_GRAVITY        = float(os.getenv("TIME_GRAVITY",        0.35))
TIME_CONSTANT       = float(os.getenv("TIME_CONSTANT",       180.0))
AFFINITY_WEIGHT     = float(os.getenv("AFFINITY_WEIGHT",     0.4))

# ── Diversity settings ─────────────────────────────────────────────────────────

MAX_PER_PUBLISHER = int(os.getenv("MAX_PER_PUBLISHER", 3))
DIVERSITY_PENALTY = float(os.getenv("DIVERSITY_PENALTY", 0.65))

# ── Cache settings ─────────────────────────────────────────────────────────────

# Reduced from 500 → 50: 50 concurrent (user, filter) combos is plenty.
RANKING_CACHE_MAX_ENTRIES = int(os.getenv("RANKING_CACHE_MAX_ENTRIES", 50))
RANKING_CACHE_TTL         = int(os.getenv("RANKING_CACHE_TTL", 300))
INTERACTION_CACHE_TTL     = int(os.getenv("INTERACTION_CACHE_TTL", 120))

# Reduced from 500 → 200: covers 10 pages of 20 items with comfortable headroom.
COMPUTE_N_RESULTS    = int(os.getenv("COMPUTE_N_RESULTS", 200))
CANDIDATE_MULTIPLIER = int(os.getenv("CANDIDATE_MULTIPLIER", 3))

# ── Payload field allowlist ────────────────────────────────────────────────────
#
# Only these fields are kept in cached items. Every other key that might
# appear in a Qdrant payload (e.g. internal ingest metadata) is dropped
# before the list is stored in RAM.
#
# Computed fields (item_id, relevance_score, similar_articles,
# cluster_summary) are added by the ranking pipeline and are also kept.
#
_PAYLOAD_FIELDS: frozenset[str] = frozenset({
    # Qdrant payload — known fields as of schema v1
    "title",
    "description",
    "author",
    "link",
    "pub_date",
    "pub_timestamp",
    "feed_sha256",
    "feed_title",
    "feed_icon",
    "url_hash",
    # Computed by the ranking pipeline
    "item_id",
    "relevance_score",
    "similar_articles",
    "cluster_summary",
})


def _slim(item: dict) -> dict:
    """Return a copy of *item* containing only allowlisted fields."""
    return {k: v for k, v in item.items() if k in _PAYLOAD_FIELDS}


# ── Thread-safe caches ─────────────────────────────────────────────────────────

_cache_lock:           threading.Lock  = threading.Lock()
_processed_list_cache: OrderedDict     = OrderedDict()

_interaction_lock:  threading.Lock              = threading.Lock()
_interaction_cache: dict[int, tuple[float, set[str]]] = {}


# ── Context manager ────────────────────────────────────────────────────────────

@contextmanager
def _get_cursor(dictionary: bool = True):
    with get_db() as conn:
        cursor = conn.cursor(dictionary=dictionary)
        try:
            yield cursor
        finally:
            cursor.close()


# ── LRU cache helpers ──────────────────────────────────────────────────────────

def _lru_get(cache: OrderedDict, key, ttl: int):
    if key not in cache:
        return None
    ts, data = cache[key]
    if time.monotonic() - ts >= ttl:
        del cache[key]
        return None
    cache.move_to_end(key)
    return data


def _lru_put(cache: OrderedDict, key, data, max_size: int) -> None:
    cache[key] = (time.monotonic(), data)
    cache.move_to_end(key)
    while len(cache) > max_size:
        cache.popitem(last=False)


# ── Public cache invalidation ──────────────────────────────────────────────────

def invalidate_cache(user_id: int | None = None) -> None:
    """Drop the processed list cache for one user, or for everyone."""
    with _cache_lock:
        if user_id is None:
            _processed_list_cache.clear()
            return
        stale = [k for k in _processed_list_cache if k[0] == user_id]
        for k in stale:
            _processed_list_cache.pop(k, None)


def invalidate_interaction_cache(user_id: int | None = None) -> None:
    with _interaction_lock:
        if user_id is None:
            _interaction_cache.clear()
        else:
            _interaction_cache.pop(user_id, None)


# ── Interacted IDs ─────────────────────────────────────────────────────────────

def _get_interacted_ids(user_id: int) -> set[str]:
    now = time.monotonic()
    with _interaction_lock:
        entry = _interaction_cache.get(user_id)
        if entry is not None:
            ts, ids = entry
            if now - ts < INTERACTION_CACHE_TTL:
                return ids

    with _get_cursor() as cursor:
        cursor.execute(
            "SELECT DISTINCT item_id FROM interactions WHERE user_id = %s",
            (user_id,),
        )
        ids: set[str] = {str(row["item_id"]) for row in cursor.fetchall()}

    with _interaction_lock:
        _interaction_cache[user_id] = (now, ids)

    return ids


def get_interacted_ids_except_view(user_id: int) -> set[str]:
    with _get_cursor() as cursor:
        cursor.execute(
            "SELECT DISTINCT item_id FROM interactions WHERE user_id = %s AND action != 'view'",
            (user_id,),
        )
        return {str(row["item_id"]) for row in cursor.fetchall()}


# ── Article stats ──────────────────────────────────────────────────────────────

def _get_article_stats_batch(item_ids: list[str]) -> dict[str, dict]:
    if not item_ids:
        return {}
    with _get_cursor() as cursor:
        fmt = ",".join(["%s"] * len(item_ids))
        cursor.execute(
            f"SELECT item_id, likes_count, dislikes_count, "
            f"views_count, saved_count, reads_count "
            f"FROM article_stats WHERE item_id IN ({fmt})",
            tuple(item_ids),
        )
        return {row["item_id"]: dict(row) for row in cursor.fetchall()}


# ── Feed-filter resolution ─────────────────────────────────────────────────────

def _resolve_feed_filter(
    user_id: int,
    folder_id: Optional[str],
    feed_sha256: Optional[str],
) -> Optional[list[str]]:
    """
    Return the list of feed hashes the query should be restricted to.
    When no explicit folder/feed filter is given, the user's subscribed
    feeds are used as the default scope so that each user only sees
    content from their own subscriptions.
    Returns an empty list if the user has no matching subscriptions
    (caller should short-circuit and return []).
    """
    feeds: set[str] = set()

    with _get_cursor() as cursor:
        if folder_id:
            cursor.execute(
                """
                SELECT ff.feed_sha256
                FROM feed_folders ff
                WHERE ff.user_id = %s AND ff.folder_id = %s
                """,
                (user_id, folder_id),
            )
            for row in cursor.fetchall():
                feeds.add(row["feed_sha256"])

        if feed_sha256:
            cursor.execute(
                """
                SELECT feed_sha256
                FROM user_subscriptions
                WHERE user_id = %s AND feed_sha256 = %s
                """,
                (user_id, feed_sha256),
            )
            row = cursor.fetchone()
            if row:
                feeds.add(row["feed_sha256"])

        if not folder_id and not feed_sha256:
            cursor.execute(
                """
                SELECT feed_sha256
                FROM user_subscriptions
                WHERE user_id = %s
                """,
                (user_id,),
            )
            for row in cursor.fetchall():
                feeds.add(row["feed_sha256"])

    return list(feeds) if feeds else []


# ── Qdrant filter builder ──────────────────────────────────────────────────────

def _build_qdrant_filter(
    max_days: int,
    feed_filter: Optional[list[str]],
) -> models.Filter:
    min_timestamp = (datetime.now(timezone.utc) - timedelta(days=max_days)).timestamp()

    must: list[models.Condition] = [
        models.FieldCondition(
            key="pub_timestamp",
            range=models.Range(gte=min_timestamp),
        )
    ]

    if feed_filter is not None:
        must.append(
            models.FieldCondition(
                key="feed_sha256",
                match=models.MatchAny(any=feed_filter),
            )
        )

    return models.Filter(must=must)


# ── User profile ───────────────────────────────────────────────────────────────

def _get_user_profile(user_id: int) -> Optional[dict]:
    with _get_cursor() as cursor:
        cursor.execute(
            """
            SELECT pos_vector, neg_vector,
                   affinity_pos_vector, affinity_neg_vector,
                   publisher_likes, publisher_dislikes, publisher_freq
              FROM user_vectors
             WHERE user_id = %s
            """,
            (user_id,),
        )
        return cursor.fetchone()


# ── Tier 1: Personalised scoring ───────────────────────────────────────────────

def _compute_personalised_list(
    user_id: int,
    n_results: int,
    max_days: int,
    feed_filter: Optional[list[str]],
) -> tuple[list[tuple[str, float]], dict[str, dict]]:
    row = _get_user_profile(user_id)

    if not row or not row.get("pos_vector"):
        logger.info("No vectors for user_id=%s — falling back to cold-start", user_id)
        return [], {}

    pos_vector: list[float] = json.loads(row["pos_vector"])
    neg_vector: Optional[list[float]] = (
        json.loads(row["neg_vector"]) if row.get("neg_vector") else None
    )
    affinity_pos: Optional[list[float]] = (
        json.loads(row["affinity_pos_vector"]) if row.get("affinity_pos_vector") else None
    )
    affinity_neg: Optional[list[float]] = (
        json.loads(row["affinity_neg_vector"]) if row.get("affinity_neg_vector") else None
    )

    query_pos = blend_vectors(pos_vector, affinity_pos, AFFINITY_WEIGHT)
    query_neg = (
        blend_vectors(neg_vector, affinity_neg, AFFINITY_WEIGHT)
        if neg_vector else None
    )

    pub_likes:    dict[str, int]   = json.loads(row["publisher_likes"])    if row.get("publisher_likes")    else {}
    pub_dislikes: dict[str, int]   = json.loads(row["publisher_dislikes"]) if row.get("publisher_dislikes") else {}
    pub_freq:     dict[str, float] = json.loads(row["publisher_freq"])     if row.get("publisher_freq")     else {}

    client           = get_qdrant_client()
    filter_condition = _build_qdrant_filter(max_days, feed_filter)
    now_ts           = time.time()
    fetch_count      = n_results * CANDIDATE_MULTIPLIER

    pos_response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_pos,
        query_filter=filter_condition,
        limit=fetch_count,
        with_payload=True,
        with_vectors=False,
    )

    if not pos_response.points:
        logger.info("No Qdrant results for user_id=%s", user_id)
        return [], {}

    neg_scores: dict[str, float] = {}
    if query_neg is not None:
        neg_response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_neg,
            query_filter=filter_condition,
            limit=fetch_count,
            with_payload=False,
            with_vectors=False,
        )
        neg_scores = {str(p.id): p.score for p in neg_response.points}

    item_ids  = [str(p.id) for p in pos_response.points]
    art_stats = _get_article_stats_batch(item_ids)

    candidates: list[tuple[str, float]] = []
    payloads:   dict[str, dict]         = {}

    for hit in pos_response.points:
        item_id = str(hit.id)
        sim_pos = hit.score
        sim_neg = neg_scores.get(item_id, 0.0)

        c_score  = contrast_score(sim_pos, sim_neg) ** CONTRAST_EXPONENT
        payload  = hit.payload
        payloads[item_id] = payload

        feed_hash = payload.get("feed_sha256")
        likes     = float(pub_likes.get(feed_hash, 0))              if feed_hash else 0.0
        dislikes  = float(pub_dislikes.get(feed_hash, 0))           if feed_hash else 0.0
        freq      = float(pub_freq.get(feed_hash, FREQ_REF_DAYS))   if feed_hash else FREQ_REF_DAYS

        eng  = publisher_engagement(likes, dislikes, ENGAGEMENT_EXPONENT)
        fbon = publisher_frequency_bonus(freq, FREQ_REF_DAYS, FREQ_EXPONENT, FREQ_BONUS_CAP)

        stats = art_stats.get(item_id, {})
        pop   = article_popularity(
            likes=stats.get("likes_count", 0),
            views=stats.get("views_count", 0),
            saved=stats.get("saved_count", 0),
            reads=stats.get("reads_count", 0),
        )

        td        = time_decay_multiplier(payload.get("pub_timestamp"), now_ts, TIME_CONSTANT, TIME_GRAVITY)
        raw_score = c_score * eng * pop * fbon * td

        candidates.append((item_id, raw_score))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[:n_results], payloads


# ── Tier 1.5: Cold-start ───────────────────────────────────────────────────────

def _compute_cold_start_list(
    max_days: int,
    feed_filter: Optional[list[str]],
    n_results: int,
) -> tuple[list[tuple[str, float]], dict[str, dict]]:
    client           = get_qdrant_client()
    filter_condition = _build_qdrant_filter(max_days, feed_filter)
    now_ts           = time.time()

    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=filter_condition,
        limit=n_results * CANDIDATE_MULTIPLIER,
        order_by=models.OrderBy(
            key="pub_timestamp",
            direction=models.Direction.DESC,
        ),
        with_payload=True,
        with_vectors=False,
    )

    if not points:
        return [], {}

    item_ids  = [str(p.id) for p in points]
    art_stats = _get_article_stats_batch(item_ids)

    candidates: list[tuple[str, float]] = []
    payloads:   dict[str, dict]         = {}

    for point in points:
        item_id        = str(point.id)
        payload        = point.payload
        payloads[item_id] = payload

        stats  = art_stats.get(item_id, {})
        pop    = article_popularity(
            likes=stats.get("likes_count", 0),
            views=stats.get("views_count", 0),
            saved=stats.get("saved_count", 0),
            reads=stats.get("reads_count", 0),
        )
        td        = time_decay_multiplier(payload.get("pub_timestamp"), now_ts, TIME_CONSTANT, TIME_GRAVITY)
        raw_score = pop * td

        candidates.append((item_id, raw_score))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[:n_results], payloads


# ── Tier 2: Chronological fallback ────────────────────────────────────────────

def _get_recent_articles(
    limit: int,
    max_days: int,
    exclude_ids: set[str],
    feed_filter: Optional[list[str]] = None,
) -> list[dict]:
    client           = get_qdrant_client()
    filter_condition = _build_qdrant_filter(max_days, feed_filter)

    # Cap fetch at 500 to avoid pulling thousands of points into memory.
    fetch_limit = min(limit * 2 + 50, 500)

    scroll_result, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=filter_condition,
        limit=fetch_limit,
        order_by=models.OrderBy(
            key="pub_timestamp",
            direction=models.Direction.DESC,
        ),
        with_payload=True,
        with_vectors=False,
    )

    recents: list[dict] = []
    for point in scroll_result:
        pid = str(point.id)
        if pid in exclude_ids:
            continue
        item = _slim(point.payload)
        item["item_id"] = pid
        recents.append(item)
        if len(recents) >= limit:
            break

    return recents


# ── Cache key ──────────────────────────────────────────────────────────────────

def _make_cache_key(
    user_id: int,
    max_days: int,
    feed_filter: Optional[list[str]],
) -> tuple:
    return (
        user_id,
        max_days,
        tuple(sorted(feed_filter)) if feed_filter is not None else None,
    )


# ── Full list builder ──────────────────────────────────────────────────────────

def _build_full_processed_list(
    user_id: int,
    max_days: int,
    feed_filter: Optional[list[str]],
) -> list[dict]:
    """
    Build, process, and cache the complete ranked list for a user.

    This runs once per cache TTL. Pagination slices from this stable list,
    guaranteeing seamless infinite scroll without skips or duplicates.

    Memory discipline
    ─────────────────
    • Payloads from Qdrant are slimmed via _slim() before caching — only
      allowlisted fields are retained.
    • Scoring intermediates (candidates, neg_scores, art_stats) are local
      and are GC'd when this function returns.
    """
    cache_key = _make_cache_key(user_id, max_days, feed_filter)

    with _cache_lock:
        cached = _lru_get(_processed_list_cache, cache_key, RANKING_CACHE_TTL)
        if cached is not None:
            return cached

    # ── 1. Raw scores and payloads ─────────────────────────────────────────
    scores, payloads = _compute_personalised_list(
        user_id, COMPUTE_N_RESULTS, max_days, feed_filter
    )
    if not scores:
        scores, payloads = _compute_cold_start_list(
            max_days, feed_filter, COMPUTE_N_RESULTS
        )

    if not scores:
        return []

    global_max_score = max(score for _, score in scores)

    # ── 2. Build slim item list from scored candidates ─────────────────────
    all_items: list[dict] = []
    for item_id, raw_score in scores:
        payload = payloads.get(item_id)
        if payload is None:
            continue
        item                   = _slim(payload)
        item["item_id"]        = item_id
        item["relevance_score"] = raw_score
        all_items.append(item)

    # ── 3. Tier-2 chronological gap-fill ──────────────────────────────────
    all_ranked_ids    = {pid for pid, _ in scores}
    slots_remaining   = COMPUTE_N_RESULTS - len(all_items)

    if slots_remaining > 0:
        recent_items = _get_recent_articles(
            limit=slots_remaining,
            max_days=max_days,
            exclude_ids=all_ranked_ids,
            feed_filter=feed_filter,
        )
        for item in recent_items:
            item["relevance_score"] = 0.0
            all_items.append(item)

    # ── 4. Sort by raw score ───────────────────────────────────────────────
    all_items.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)

    # ── 5. Cluster deduplication ───────────────────────────────────────────
    all_items = _apply_cluster_dedup(all_items)

    # ── 6. Publisher diversity penalty ────────────────────────────────────
    all_items = _apply_diversity_penalty(all_items)

    # ── 7. Normalise scores globally ──────────────────────────────────────
    _finalize_scores(all_items, global_max_score)

    # ── 8. Cache slim list ─────────────────────────────────────────────────
    # _slim() has already been called at construction time for payload items.
    # Run it once more to ensure pipeline-added fields (similar_articles,
    # cluster_summary) are included but nothing else slipped in.
    slim_list = [_slim(item) for item in all_items]

    with _cache_lock:
        _lru_put(_processed_list_cache, cache_key, slim_list, RANKING_CACHE_MAX_ENTRIES)

    return slim_list


# ── Cluster deduplication ──────────────────────────────────────────────────────

def _apply_cluster_dedup(items: list[dict]) -> list[dict]:
    cluster_index    = get_cluster_index()
    cluster_summaries = get_cluster_summaries()

    if not cluster_index:
        return items

    id_to_pos:           dict[str, int] = {item["item_id"]: i for i, item in enumerate(items) if item.get("item_id")}
    consumed_as_sibling: set[str]       = set()

    for item in items:
        iid = item.get("item_id")
        if not iid or iid in consumed_as_sibling:
            continue

        siblings = cluster_index.get(iid, [])
        if not siblings:
            continue

        visible_siblings: list[dict] = []
        for sib in siblings:
            sib_id = sib.get("item_id")
            if sib_id and sib_id in id_to_pos and sib_id not in consumed_as_sibling:
                visible_siblings.append(sib)
                consumed_as_sibling.add(sib_id)

        if visible_siblings:
            item["similar_articles"] = visible_siblings
            item["cluster_summary"]  = cluster_summaries.get(iid, "")

    return [item for item in items if item.get("item_id") not in consumed_as_sibling]


# ── Publisher diversity penalty ────────────────────────────────────────────────

def _apply_diversity_penalty(
    items:             list[dict],
    max_per_publisher: int   = MAX_PER_PUBLISHER,
    penalty_factor:    float = DIVERSITY_PENALTY,
) -> list[dict]:
    if max_per_publisher <= 0 or not items:
        return items

    publisher_count: dict[str, int] = {}

    for item in items:
        feed_hash = item.get("feed_sha256", "")
        count     = publisher_count.get(feed_hash, 0)
        publisher_count[feed_hash] = count + 1

        if count >= max_per_publisher:
            excess = count - max_per_publisher + 1
            item["relevance_score"] *= penalty_factor ** excess

    items.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)
    return items


# ── Score normalisation ────────────────────────────────────────────────────────

def _finalize_scores(items: list[dict], global_max_score: float) -> None:
    """Normalise raw scores to [0, 1] and enforce strict monotonic non-increase."""
    if not items:
        return

    items.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)

    if global_max_score > 0:
        for item in items:
            raw  = item.get("relevance_score", 0.0)
            norm = max(0.0, min(1.0, raw / global_max_score))
            item["relevance_score"] = round(norm, 4)
    else:
        for item in items:
            item["relevance_score"] = 0.0

    # Safety net: rounding can create tiny inversions — clamp them.
    for i in range(1, len(items)):
        prev = items[i - 1]["relevance_score"]
        curr = items[i]["relevance_score"]
        if curr > prev:
            items[i]["relevance_score"] = prev


# ── Feed metadata fallback ─────────────────────────────────────────────────────

def _fill_missing_feed_metadata(page_items: list[dict]) -> None:
    """
    Back-fill feed_title / feed_icon from MySQL for items where the Qdrant
    payload didn't carry those fields (e.g. older indexed articles).

    This is a targeted fallback — it only fires when at least one item on
    the current page is missing the fields, and only fetches the feeds that
    are actually needed.
    """
    missing_hashes: set[str] = {
        item["feed_sha256"]
        for item in page_items
        if item.get("feed_sha256")
        and (not item.get("feed_title") or not item.get("feed_icon"))
    }

    if not missing_hashes:
        return

    with _get_cursor() as cursor:
        fmt = ",".join(["%s"] * len(missing_hashes))
        cursor.execute(
            f"SELECT feed_sha256, feed_title, feed_icon "
            f"FROM feeds WHERE feed_sha256 IN ({fmt})",
            tuple(missing_hashes),
        )
        feeds_info: dict[str, dict] = {
            row["feed_sha256"]: row for row in cursor.fetchall()
        }

    for item in page_items:
        f_hash = item.get("feed_sha256")
        if f_hash not in feeds_info:
            continue
        info = feeds_info[f_hash]
        if not item.get("feed_title"):
            item["feed_title"] = info["feed_title"]
        if not item.get("feed_icon"):
            item["feed_icon"] = info["feed_icon"]


# ── Public API ─────────────────────────────────────────────────────────────────

def get_recommendations(
    user_id:    int,
    page:       int           = 1,
    limit:      int           = 20,
    max_days:   int           = 30,
    folder_id:  Optional[str] = None,
    feed_sha256: Optional[str] = None,
) -> list[dict]:
    """
    Return one page of ranked articles for *user_id*.

    Pages are 0-indexed (page=0 → items 0–19, page=1 → 20–39, …).
    All scoring and normalisation happen once per cache TTL; pagination
    is a simple slice over the cached list, so it is O(1) after the
    first call.
    """
    # 1. Resolve optional feed/folder filter
    feed_filter = _resolve_feed_filter(user_id, folder_id, feed_sha256)
    if feed_filter is not None and len(feed_filter) == 0:
        return []

    # 2. Retrieve (or build) the fully processed, globally normalised list
    full_list = _build_full_processed_list(user_id, max_days, feed_filter)

    # 3. Exclude already-interacted articles (dynamic, not cached)
    interacted_ids = _get_interacted_ids(user_id)
    visible_items  = [
        item for item in full_list
        if item.get("item_id") not in interacted_ids
    ]

    # 4. Page slice
    page       = max(0, page)
    start      = page * limit
    end        = start + limit
    page_items = visible_items[start:end]

    # 5. Fill missing feed metadata (only when Qdrant payload is incomplete)
    _fill_missing_feed_metadata(page_items)

    return page_items