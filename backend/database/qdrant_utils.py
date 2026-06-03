"""
database/qdrant_utils.py — Qdrant CRUD helpers and publisher frequency.
"""

from __future__ import annotations

import uuid
import json
import logging
from datetime import datetime, timedelta, timezone

from intelligence.embeddings import get_qdrant_client, COLLECTION_NAME, TAG_PHRASES_COLLECTION
from database.init_db import get_db
from qdrant_client.http import models
from qdrant_client.http.models import PointStruct

logger = logging.getLogger(__name__)


# ── Article lookup ─────────────────────────────────────────────────────────────

def get_article_point(identifier: str, with_vector: bool = False):
    """
    Locate an article in Qdrant by UUID or URL hash.

    Strategy:
      1. Try as UUID — O(1) lookup by point ID.
      2. Fall back to url_hash payload filter.

    Returns the point record or None.
    """
    client = get_qdrant_client()

    # 1. UUID lookup
    try:
        uuid_obj = uuid.UUID(identifier)
        points = client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[str(uuid_obj)],
            with_vectors=with_vector,
            with_payload=True,
        )
        if points:
            return points[0]
    except ValueError:
        pass

    # 2. url_hash lookup
    scroll_result = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="url_hash",
                    match=models.MatchValue(value=identifier),
                )
            ]
        ),
        limit=1,
        with_payload=True,
        with_vectors=with_vector,
    )
    if scroll_result[0]:
        return scroll_result[0][0]

    return None


# ── CRUD helpers ───────────────────────────────────────────────────────────────

def add_item_to_qdrant(item_id: str, embedding: list, payload: dict):
    """Add or replace a single item in Qdrant."""
    client = get_qdrant_client()
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[PointStruct(id=item_id, vector=embedding, payload=payload)],
    )


def add_items_batch(points: list):
    """Add multiple PointStruct items in batch."""
    client = get_qdrant_client()
    client.upsert(collection_name=COLLECTION_NAME, points=points)


def search_similar(
    embedding: list,
    filter_condition=None,
    limit: int = 10,
    score_threshold: float | None = None,
) -> list:
    """Search for similar items using cosine similarity via Qdrant ANN."""
    client = get_qdrant_client()
    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=embedding,
        query_filter=filter_condition,
        limit=limit,
        score_threshold=score_threshold,
        with_payload=True,
        with_vectors=False,
    )
    return response.points


def retrieve_items(item_ids: list) -> list:
    """Retrieve points by IDs (with payload, without vectors)."""
    client = get_qdrant_client()
    return client.retrieve(
        collection_name=COLLECTION_NAME,
        ids=item_ids,
        with_payload=True,
        with_vectors=False,
    )


# ── Publisher frequency ────────────────────────────────────────────────────────

def count_posts_per_feed(
    feed_hashes: list[str],
    days: int = 30,
) -> dict[str, int]:
    """
    Count articles per publisher in the last N days.
    Uses Qdrant's count API per feed instead of a full scroll.
    """
    if not feed_hashes:
        return {}

    client = get_qdrant_client()
    min_timestamp = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()

    counts: dict[str, int] = {}
    for fh in feed_hashes:
        try:
            result = client.count(
                collection_name=COLLECTION_NAME,
                count_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="pub_timestamp",
                            range=models.Range(gte=min_timestamp),
                        ),
                        models.FieldCondition(
                            key="feed_sha256",
                            match=models.MatchValue(value=fh),
                        ),
                    ]
                ),
            )
            counts[fh] = result.count
        except Exception as exc:
            logger.warning("Failed to count posts for feed %s: %s", fh[:8], exc)
            counts[fh] = 0

    return counts


def refresh_publisher_freq(
    user_id: int,
    feed_hashes: list[str],
    days: int = 30,
) -> None:
    """Recompute and persist publisher_freq for a specific user."""
    freq_map = count_posts_per_feed(feed_hashes, days=days)

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    UPDATE user_vectors
                    SET publisher_freq = %s
                    WHERE user_id = %s
                    """,
                    (json.dumps(freq_map), user_id),
                )
                logger.debug(
                    "publisher_freq updated for user_id=%s (%d feeds)",
                    user_id, len(freq_map),
                )
            finally:
                cursor.close()
    except Exception as exc:
        logger.error("Error updating publisher_freq for user_id=%s: %s", user_id, exc)


# ── Index management ───────────────────────────────────────────────────────────

def ensure_payload_indexes() -> None:
    """Ensure payload indices exist on the Qdrant collection."""
    client = get_qdrant_client()

    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="title",
        field_schema=models.TextIndexParams(
            type="text",
            tokenizer=models.TokenizerType.WORD,
            lowercase=True,
        ),
    )
    logger.info("Payload index ensured: title (text)")

    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="pub_timestamp",
        field_schema=models.PayloadSchemaType.FLOAT,
    )
    logger.info("Payload index ensured: pub_timestamp (float)")

    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="feed_sha256",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    logger.info("Payload index ensured: feed_sha256 (keyword)")


# Backward compatibility alias
ensure_text_indexes = ensure_payload_indexes


# ── Tag phrases collection ────────────────────────────────────────────────────

def upsert_tag_phrase(tag_id: int, term: str, vector: list[float], manual_count: int = 0) -> None:
    client = get_qdrant_client()
    client.upsert(
        collection_name=TAG_PHRASES_COLLECTION,
        points=[PointStruct(
            id=str(tag_id),
            vector=vector,
            payload={"term": term, "tag_id": tag_id, "manual_count": manual_count},
        )],
    )


def delete_tag_phrase(tag_id: int) -> None:
    client = get_qdrant_client()
    try:
        client.delete(
            collection_name=TAG_PHRASES_COLLECTION,
            points_selector=models.PointIdsList(points=[str(tag_id)]),
        )
    except Exception:
        logger.warning("Could not delete tag phrase vector for tag_id=%d", tag_id)


def search_tag_phrases(vector: list[float], limit: int = 10, threshold: float = 0.0) -> list:
    client = get_qdrant_client()
    response = client.query_points(
        collection_name=TAG_PHRASES_COLLECTION,
        query=vector,
        limit=limit,
        score_threshold=threshold if threshold > 0.0 else None,
        with_payload=True,
        with_vectors=False,
    )
    return response.points