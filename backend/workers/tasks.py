"""
tasks.py — Background job definitions for the arq worker.
"""

import asyncio
import aiohttp
import json
import logging
import os
import re as _re
from database.init_db import get_db
from rss.parser import parse_and_save_feed_async
from intelligence.cluster import compute_weekly_events, set_cached_events, load_events_from_db
from intelligence.cluster_store import build_reverse_index, set_cluster_index
from intelligence.embeddings import get_qdrant_client, COLLECTION_NAME, get_current_fingerprint
from arq import cron
from arq.connections import RedisSettings

logger = logging.getLogger(__name__)

MAX_CONCURRENT = int(os.getenv("FEED_PARSE_MAX_CONCURRENT", "2"))
STALE_HOURS = int(os.getenv("FEED_STALE_HOURS", "6"))
_raw_cron = os.getenv("FEED_REFRESH_CRON_HOURS", "0,6,12,18").strip()
REFRESH_CRON_HOURS = {int(h) for h in _raw_cron.split(",")} if _raw_cron else {0, 6, 12, 18}


# ── Feed refresh ───────────────────────────────────────────────────────────────

def _get_all_feeds_sync() -> list[dict]:
    """Synchronous DB call to get all feeds."""
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT feed_url, feed_sha256 FROM feeds")
            return cursor.fetchall()
        finally:
            cursor.close()


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


async def _refresh_feeds(feeds: list[dict]) -> dict:
    """Parse a list of feeds concurrently and return result count."""
    if not feeds:
        return {"refreshed": 0}

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def parse_one(session, feed_url):
        async with semaphore:
            return await parse_and_save_feed_async(session, feed_url)

    async with aiohttp.ClientSession() as session:
        await asyncio.gather(
            *[parse_one(session, row["feed_url"]) for row in feeds],
            return_exceptions=True,
        )

    feed_hashes = [row["feed_sha256"] for row in feeds if row.get("feed_sha256")]
    if feed_hashes:
        await _refresh_freq_for_affected_users(feed_hashes)
        user_feeds = await asyncio.to_thread(_get_affected_users_and_feeds_sync, feed_hashes)
        affected_user_ids = list(user_feeds.keys())
        if affected_user_ids:
            await asyncio.to_thread(_evaluate_tags_for_users_sync, affected_user_ids)

    return {"refreshed": len(feeds)}


async def refresh_stale_feeds(ctx):
    """Parse all feeds not updated in the last STALE_HOURS."""
    stale = await asyncio.to_thread(_get_stale_feeds_sync)
    return await _refresh_feeds(stale)


async def refresh_all_feeds(ctx):
    """Parse every feed regardless of staleness."""
    all_feeds = await asyncio.to_thread(_get_all_feeds_sync)
    return await _refresh_feeds(all_feeds)


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
    await asyncio.to_thread(_evaluate_tags_for_users_sync, [user_id])
    return result


async def refresh_weekly_events(ctx):
    logger.info("Starting weekly events refresh...")
    redis = ctx["redis"]

    try:
        events = await asyncio.to_thread(compute_weekly_events)
    except Exception as e:
        logger.error("refresh_weekly_events: compute_weekly_events failed: %s", e, exc_info=True)
        events = await asyncio.to_thread(load_events_from_db) or []

    if events:
        try:
            await set_cached_events(redis, events)
        except Exception as e:
            logger.error("refresh_weekly_events: failed to cache events: %s", e)

    reverse_index = {}
    try:
        reverse_index, summaries = build_reverse_index(events)
        set_cluster_index(reverse_index, summaries)
    except Exception as e:
        logger.error("refresh_weekly_events: failed to build reverse index: %s", e)

    logger.info(
        "Weekly events refresh complete: %d events, %d mapped articles",
        len(events), len(reverse_index),
    )
    return {"events_generated": len(events)}


# ── Re-embedding job (triggered on model change) ───────────────────────────────

def _reembed_all_sync() -> dict:
    from intelligence.embeddings import (
        get_embedding_model, get_qdrant_client, embedding_text,
        build_embedding_text, COLLECTION_NAME, _SENTINEL_ID, get_current_fingerprint,
    )
    from qdrant_client.http import models as qmodels

    client = get_qdrant_client()
    model = get_embedding_model()
    fp = get_current_fingerprint()

    logger.info("[RE-EMBED] Starting full re-embedding with fingerprint=%s", fp)

    all_points = []
    offset = None
    while True:
        points, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            with_vectors=True,
            with_payload=True,
            limit=500,
            offset=offset,
        )
        all_points.extend(points)
        if next_offset is None:
            break
        offset = next_offset

    re_embeded = 0
    skipped = 0
    for point in all_points:
        if str(point.id) == _SENTINEL_ID:
            continue
        payload = point.payload or {}
        if payload.get("_model_fp") == fp:
            skipped += 1
            continue
        title = payload.get("title", "")
        if not title:
            skipped += 1
            continue
        description = payload.get("description", "")
        new_vector = embedding_text(build_embedding_text(title, description))
        payload["_model_fp"] = fp
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[{"id": str(point.id), "vector": new_vector, "payload": payload}],
        )
        re_embeded += 1

    from database.init_db import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE user_vectors SET pos_vector = '[]', neg_vector = NULL, "
                "affinity_pos_vector = NULL, affinity_neg_vector = NULL "
                "WHERE pos_vector != '[]' OR neg_vector IS NOT NULL "
                "OR affinity_pos_vector IS NOT NULL OR affinity_neg_vector IS NOT NULL"
            )
            reset = cursor.rowcount
            conn.commit()
        finally:
            cursor.close()

    logger.info(
        "[RE-EMBED] Complete: %d re-embedded, %d skipped, %d user vectors reset",
        re_embeded, skipped, reset,
    )
    return {"re_embeded": re_embeded, "skipped": skipped, "user_vectors_reset": reset}


async def reembed_all(ctx):
    result = await asyncio.to_thread(_reembed_all_sync)
    return result


# ── Re-image job (patches image_url for articles that already have content) ─

def _reimage_all_sync() -> dict:
    """Scroll all Qdrant points and patch image_url by extracting from description HTML."""
    from intelligence.embeddings import get_qdrant_client, COLLECTION_NAME

    client = get_qdrant_client()

    logger.info("[RE-IMAGE] Starting image URL backfill")

    updated = 0
    offset = None
    while True:
        points, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            with_payload=True,
            with_vectors=False,
            limit=500,
            offset=offset,
        )

        for point in points:
            payload = point.payload or {}
            if payload.get("image_url") is not None:
                continue

            description = payload.get("description", "")
            if not description:
                continue

            match = _re.search(r'<img[^>]+src=["\']([^"\']+)["\']', description, _re.IGNORECASE)
            if not match:
                continue

            url = match.group(1).strip()
            if not url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')):
                continue

            client.set_payload(
                collection_name=COLLECTION_NAME,
                payload={"image_url": url},
                points=[str(point.id)],
            )
            updated += 1

        if next_offset is None:
            break
        offset = next_offset

    logger.info("[RE-IMAGE] Complete: %d updated", updated)
    return {"updated": updated}


async def reimage_all(ctx):
    result = await asyncio.to_thread(_reimage_all_sync)
    return result


# ── Smart Tags auto-evaluation ────────────────────────────────────────────────

def _safe_json_parse(val):
    if val is None:
        return []
    if isinstance(val, (list, dict)):
        return val
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return []


def _evaluate_tags_list(tags: list[dict], client, BATCH_SIZE: int = 256) -> dict:
    import re
    import numpy as np
    from intelligence.embeddings import get_qdrant_client, embedding_text, COLLECTION_NAME
    from database.qdrant_utils import upsert_tag_phrase, delete_tag_phrase
    from qdrant_client.http import models as qmodels

    seen_users: set[int] = set()
    del_count = 0
    total_assignments = 0

    for tag in tags:
        tag_id = tag["id"]
        user_id = tag["user_id"]

        if user_id not in seen_users:
            seen_users.add(user_id)
            with get_db() as conn:
                c = conn.cursor()
                try:
                    c.execute(
                        "DELETE FROM article_tags WHERE user_id = %s AND source != 'manual'",
                        (user_id,),
                    )
                    del_count += c.rowcount
                    conn.commit()
                finally:
                    c.close()

        layers = (tag.get("enabled_layers") or "").split(",")

        feed_scope_set = set()
        folder_scope_set = set()
        if "feed" in layers and tag.get("feed_scope"):
            parsed = _safe_json_parse(tag["feed_scope"])
            if isinstance(parsed, list):
                feed_scope_set.update(parsed)
        if "folder" in layers and tag.get("folder_scope"):
            folder_ids = _safe_json_parse(tag["folder_scope"])
            if isinstance(folder_ids, list) and folder_ids:
                with get_db() as conn:
                    cursor = conn.cursor(dictionary=True)
                    try:
                        fmt = ",".join(["%s"] * len(folder_ids))
                        cursor.execute(
                            f"SELECT feed_sha256 FROM feed_folders "
                            f"WHERE user_id = %s AND folder_id IN ({fmt})",
                            [user_id] + list(folder_ids),
                        )
                        for row in cursor.fetchall():
                            folder_scope_set.add(row["feed_sha256"])
                    finally:
                        cursor.close()

        scope_feeds = feed_scope_set | folder_scope_set

        # ── Feed layer ──────────────────────────────────────────
        if "feed" in layers and feed_scope_set:
            candidate_ids: list[str] = []
            feed_filter = qmodels.Filter(
                must=[qmodels.FieldCondition(
                    key="feed_sha256",
                    match=qmodels.MatchAny(any=list(feed_scope_set)),
                )]
            )
            offset = None
            while True:
                points, next_offset = client.scroll(
                    collection_name=COLLECTION_NAME,
                    scroll_filter=feed_filter,
                    limit=500,
                    offset=offset,
                    with_payload=False,
                    with_vectors=False,
                )
                candidate_ids.extend(str(p.id) for p in points)
                if next_offset is None:
                    break
                offset = next_offset

            batch_rows = [
                (user_id, iid, tag_id, "feed")
                for iid in candidate_ids
            ]
            for i in range(0, len(batch_rows), BATCH_SIZE):
                with get_db() as conn:
                    cursor = conn.cursor()
                    try:
                        cursor.executemany(
                            "INSERT IGNORE INTO article_tags "
                            "(user_id, item_id, tag_id, source) VALUES (%s, %s, %s, %s)",
                            batch_rows[i:i + BATCH_SIZE],
                        )
                        conn.commit()
                    finally:
                        cursor.close()
            total_assignments += len(batch_rows)

        # ── Folder layer ────────────────────────────────────────
        if "folder" in layers and folder_scope_set:
            candidate_ids: list[str] = []
            folder_filter = qmodels.Filter(
                must=[qmodels.FieldCondition(
                    key="feed_sha256",
                    match=qmodels.MatchAny(any=list(folder_scope_set)),
                )]
            )
            offset = None
            while True:
                points, next_offset = client.scroll(
                    collection_name=COLLECTION_NAME,
                    scroll_filter=folder_filter,
                    limit=500,
                    offset=offset,
                    with_payload=False,
                    with_vectors=False,
                )
                candidate_ids.extend(str(p.id) for p in points)
                if next_offset is None:
                    break
                offset = next_offset

            batch_rows = [
                (user_id, iid, tag_id, "folder")
                for iid in candidate_ids
            ]
            for i in range(0, len(batch_rows), BATCH_SIZE):
                with get_db() as conn:
                    cursor = conn.cursor()
                    try:
                        cursor.executemany(
                            "INSERT IGNORE INTO article_tags "
                            "(user_id, item_id, tag_id, source) VALUES (%s, %s, %s, %s)",
                            batch_rows[i:i + BATCH_SIZE],
                        )
                        conn.commit()
                    finally:
                        cursor.close()
            total_assignments += len(batch_rows)

        # ── Regex layer ─────────────────────────────────────────
        if "regex" in layers and tag.get("regex_pattern"):
            try:
                flags = 0
                raw_flags = tag.get("regex_flags") or ""
                if "i" in raw_flags:
                    flags |= re.IGNORECASE
                compiled = re.compile(tag["regex_pattern"], flags)
            except re.error as e:
                logger.warning("Invalid regex for tag %d: %s", tag_id, e)
                compiled = None

            if compiled:
                regex_filter = None
                if scope_feeds:
                    regex_filter = qmodels.Filter(
                        must=[qmodels.FieldCondition(
                            key="feed_sha256",
                            match=qmodels.MatchAny(any=list(scope_feeds)),
                        )]
                    )

                regex_batch: list[tuple] = []
                offset = None
                while True:
                    points, next_offset = client.scroll(
                        collection_name=COLLECTION_NAME,
                        scroll_filter=regex_filter,
                        limit=500,
                        offset=offset,
                        with_payload=True,
                        with_vectors=False,
                    )
                    for p in points:
                        payload = p.payload or {}
                        title = payload.get("title", "")
                        desc = payload.get("description", "")
                        search_text = f"{title} {desc}"
                        try:
                            if compiled.search(search_text):
                                regex_batch.append(
                                    (user_id, str(p.id), tag_id, "regex")
                                )
                        except re.error:
                            logger.warning(
                                "Regex error for tag %d on article %s",
                                tag_id, str(p.id)[:16],
                            )
                    if next_offset is None:
                        break
                    offset = next_offset

                for i in range(0, len(regex_batch), BATCH_SIZE):
                    with get_db() as conn:
                        cursor = conn.cursor()
                        try:
                            cursor.executemany(
                                "INSERT IGNORE INTO article_tags "
                                "(user_id, item_id, tag_id, source) VALUES (%s, %s, %s, %s)",
                                regex_batch[i:i + BATCH_SIZE],
                            )
                            conn.commit()
                        finally:
                            cursor.close()

                total_assignments += len(regex_batch)
                logger.info("Tag %d regex: %d matches", tag_id, len(regex_batch))

        # ── AI / Semantic layer ─────────────────────────────────
        centroid = None
        if "ai" in layers:
            include_terms = _safe_json_parse(tag.get("ai_include_terms"))
            if not isinstance(include_terms, list):
                include_terms = []
            exclude_terms = _safe_json_parse(tag.get("ai_exclude_terms"))
            if not isinstance(exclude_terms, list):
                exclude_terms = []

            threshold = float(tag.get("ai_threshold") or 0.65)
            negate_threshold = tag.get("ai_negate_threshold")
            if negate_threshold is not None:
                exclude_threshold = float(negate_threshold)
            else:
                exclude_threshold = min(0.90, threshold + 0.20)

            reinforcement_enabled = bool(tag.get("ai_reinforcement_enabled", 1))

            exclude_vectors = [
                np.array(embedding_text(t.strip()), dtype=np.float32)
                for t in exclude_terms if t.strip()
            ]

            raw_centroid = tag.get("centroid_vector")
            if raw_centroid is not None and len(raw_centroid) > 0:
                try:
                    centroid = np.frombuffer(raw_centroid, dtype=np.float32).copy()
                    if centroid.shape[0] == 0:
                        centroid = None
                except Exception:
                    logger.warning("Tag %d: corrupt centroid_vector, re-seeding", tag_id)
                    centroid = None

            if centroid is None:
                term_vectors = [
                    np.array(embedding_text(t.strip()), dtype=np.float32)
                    for t in include_terms if t.strip()
                ]
                if term_vectors:
                    centroid = np.mean(term_vectors, axis=0)
                    centroid = centroid / (np.linalg.norm(centroid) + 1e-8)
                    logger.info("Tag %d: seeded centroid from %d include terms", tag_id, len(term_vectors))
                else:
                    logger.warning("Tag %d: AI layer enabled but no include terms and no centroid — skipping", tag_id)
                    centroid = None

            if centroid is not None and include_terms:
                ai_filter = None
                if scope_feeds:
                    ai_filter = qmodels.Filter(
                        must=[qmodels.FieldCondition(
                            key="feed_sha256",
                            match=qmodels.MatchAny(any=list(scope_feeds)),
                        )]
                    )

                from qdrant_client.http.models import SearchParams, QuantizationSearchParams

                response = client.query_points(
                    collection_name=COLLECTION_NAME,
                    query=centroid.tolist(),
                    query_filter=ai_filter,
                    limit=500,
                    score_threshold=threshold,
                    search_params=SearchParams(
                        quantization=QuantizationSearchParams(
                            rescore=True,
                            ignore=False,
                        ),
                    ),
                    with_payload=True,
                    with_vectors=False,
                )

                ai_batch: list[tuple] = []
                if exclude_vectors:
                    ids_to_check = [str(h.id) for h in response.points]
                    retrieved = client.retrieve(
                        collection_name=COLLECTION_NAME,
                        ids=ids_to_check,
                        with_vectors=True,
                    )
                    vec_map = {str(r.id): np.array(r.vector, dtype=np.float32) for r in retrieved if r.vector is not None}
                else:
                    vec_map = {}

                for hit in response.points:
                    pid = str(hit.id)
                    if exclude_vectors:
                        art_vec = vec_map.get(pid)
                        if art_vec is not None:
                            excluded = False
                            for ex_vec in exclude_vectors:
                                sim = float(np.dot(art_vec, ex_vec) / (
                                    np.linalg.norm(art_vec) * np.linalg.norm(ex_vec) + 1e-8
                                ))
                                if sim > exclude_threshold:
                                    excluded = True
                                    break
                            if excluded:
                                continue

                    ai_batch.append(
                        (user_id, pid, tag_id, "ai", round(hit.score, 4))
                    )

                for i in range(0, len(ai_batch), BATCH_SIZE):
                    with get_db() as conn:
                        cursor = conn.cursor()
                        try:
                            cursor.executemany(
                                "INSERT IGNORE INTO article_tags "
                                "(user_id, item_id, tag_id, source, confidence) "
                                "VALUES (%s, %s, %s, %s, %s)",
                                ai_batch[i:i + BATCH_SIZE],
                            )
                            conn.commit()
                        finally:
                            cursor.close()

                total_assignments += len(ai_batch)
                logger.info(
                    "Tag %d AI centroid: %d matches (threshold=%.2f, exclude_threshold=%.2f)",
                    tag_id, len(ai_batch), threshold, exclude_threshold,
                )

            # ── Centroid refinement from manual tags ──────────
            with get_db() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "SELECT item_id FROM article_tags "
                        "WHERE user_id = %s AND tag_id = %s AND source = 'manual'",
                        (user_id, tag_id),
                    )
                    manual_ids = [str(row[0]) for row in cursor.fetchall()]
                finally:
                    cursor.close()

            n_manual = len(manual_ids)
            if n_manual > 0 and centroid is not None and reinforcement_enabled:
                retrieved = client.retrieve(
                    collection_name=COLLECTION_NAME,
                    ids=manual_ids,
                    with_vectors=True,
                    with_payload=False,
                )
                manual_vecs = [
                    np.array(r.vector, dtype=np.float32)
                    for r in retrieved if r.vector is not None
                ]
                if manual_vecs:
                    manual_centroid = np.mean(manual_vecs, axis=0)
                    manual_centroid = manual_centroid / (np.linalg.norm(manual_centroid) + 1e-8)
                    alpha = max(0.3, 1.0 - (len(manual_vecs) / (len(manual_vecs) + 5.0)))
                    centroid = alpha * centroid + (1 - alpha) * manual_centroid
                    centroid = centroid / (np.linalg.norm(centroid) + 1e-8)

                    with get_db() as conn:
                        cursor = conn.cursor()
                        try:
                            cursor.execute(
                                "UPDATE smart_tags SET centroid_vector = %s, centroid_manual_count = %s "
                                "WHERE id = %s",
                                (centroid.tobytes(), len(manual_vecs), tag_id),
                            )
                            conn.commit()
                        finally:
                            cursor.close()

                    try:
                        upsert_tag_phrase(tag_id, "", centroid.tolist(), manual_count=len(manual_vecs))
                    except Exception:
                        logger.warning("Tag %d: failed to upsert centroid to Qdrant", tag_id)

                    logger.info(
                        "Tag %d: centroid refined (alpha=%.2f, manual=%d, total_manual_ids=%d)",
                        tag_id, alpha, len(manual_vecs), n_manual,
                    )

    logger.info(
        "Tag evaluation complete: %d auto-deleted, %d assignments",
        del_count, total_assignments,
    )
    return {
        "tags_evaluated": len(tags),
        "auto_deleted": del_count,
        "total_assignments": total_assignments,
    }


def _evaluate_tags_sync() -> dict:
    from intelligence.embeddings import get_qdrant_client, COLLECTION_NAME, is_model_changed
    from intelligence.embeddings import TAG_PHRASES_COLLECTION

    client = get_qdrant_client()

    model_changed = is_model_changed()
    if model_changed:
        logger.warning("Model fingerprint changed — all tag centroids will be re-seeded")

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, user_id, name, feed_scope, folder_scope, "
                "regex_pattern, regex_flags, ai_include_terms, ai_exclude_terms, "
                "ai_threshold, ai_negate_threshold, ai_reinforcement_enabled, "
                "enabled_layers, centroid_vector, centroid_manual_count "
                "FROM smart_tags WHERE enabled_layers IS NOT NULL "
                "AND enabled_layers != ''"
            )
            tags = cursor.fetchall()
        finally:
            cursor.close()

    if model_changed:
        with get_db() as conn:
            c = conn.cursor()
            try:
                c.execute("UPDATE smart_tags SET centroid_vector = NULL, centroid_manual_count = 0")
                conn.commit()
            finally:
                c.close()
        try:
            client.delete_collection(TAG_PHRASES_COLLECTION)
            logger.info("Dropped stale tag_phrases collection (model changed)")
        except Exception:
            pass
        from intelligence.embeddings import _ensure_collection
        _ensure_collection(client)

    if not tags:
        return {"tags_evaluated": 0, "auto_deleted": 0}

    return _evaluate_tags_list(tags, client)


def _evaluate_tags_for_users_sync(user_ids: list[int]) -> dict:
    from intelligence.embeddings import get_qdrant_client

    if not user_ids:
        return {"tags_evaluated": 0, "auto_deleted": 0}

    client = get_qdrant_client()

    fmt = ",".join(["%s"] * len(user_ids))
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, user_id, name, feed_scope, folder_scope, "
                "regex_pattern, regex_flags, ai_include_terms, ai_exclude_terms, "
                "ai_threshold, ai_negate_threshold, ai_reinforcement_enabled, "
                "enabled_layers, centroid_vector, centroid_manual_count "
                f"FROM smart_tags WHERE enabled_layers IS NOT NULL "
                f"AND enabled_layers != '' AND user_id IN ({fmt})",
                user_ids,
            )
            tags = cursor.fetchall()
        finally:
            cursor.close()

    if not tags:
        return {"tags_evaluated": 0, "auto_deleted": 0}

    return _evaluate_tags_list(tags, client)


async def refresh_auto_tags(ctx):
    result = await asyncio.to_thread(_evaluate_tags_sync)
    return result


async def refresh_auto_tags_for_users(ctx, user_ids: list[int]):
    result = await asyncio.to_thread(_evaluate_tags_for_users_sync, user_ids)
    return result


# ── Worker lifecycle ───────────────────────────────────────────────────────────

def _wait_for_db_sync() -> None:
    import time
    for _ in range(10):
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM feeds LIMIT 1")
                cursor.close()
                return
        except Exception:
            time.sleep(2)


async def startup(ctx):
    await asyncio.to_thread(_wait_for_db_sync)
    await refresh_all_feeds(ctx)
    await refresh_weekly_events(ctx)
    await refresh_auto_tags(ctx)


# ── Worker settings ────────────────────────────────────────────────────────────

class WorkerSettings:
    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
    )
    on_startup = startup
    functions = [
        refresh_stale_feeds,
        refresh_all_feeds,
        refresh_weekly_events,
        refresh_all_publisher_freq,
        parse_feeds_for_user,
        reembed_all,
        reimage_all,
        refresh_auto_tags,
        refresh_auto_tags_for_users,
    ]
    cron_jobs = [
        cron(refresh_stale_feeds, hour=REFRESH_CRON_HOURS, minute=0),
        cron(refresh_weekly_events, hour=REFRESH_CRON_HOURS, minute=30),
        cron(refresh_all_publisher_freq, hour=3, minute=0),
        cron(refresh_auto_tags, hour=4, minute=0),
    ]