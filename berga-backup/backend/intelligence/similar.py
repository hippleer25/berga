import logging
import uuid

from fastapi import HTTPException
from database.qdrant_utils import search_similar, retrieve_items
from intelligence.embeddings import get_qdrant_client, COLLECTION_NAME
from database.init_db import get_db
from qdrant_client.http import models

logger = logging.getLogger(__name__)


def get_similar_articles(
    item_identifier: str,
    limit: int = 10,
    min_similarity: float = 0.7,
    max_days: int = 3,
):
    logger.debug(
        "[SIMILAR] item_identifier=%s, limit=%d, min_similarity=%.2f, max_days=%d",
        item_identifier, limit, min_similarity, max_days,
    )

    client = get_qdrant_client()
    point = None

    try:
        uuid_obj = uuid.UUID(item_identifier)
        points = retrieve_items([str(uuid_obj)])
        if points:
            point = points[0]
            logger.debug("[SIMILAR] Found by UUID")
    except ValueError:
        pass

    if point is None:
        scroll_result = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="url_hash",
                        match=models.MatchValue(value=item_identifier),
                    )
                ]
            ),
            limit=1,
            with_payload=True,
            with_vectors=False,
        )
        if scroll_result[0]:
            point = scroll_result[0][0]
            logger.debug("[SIMILAR] Found by url_hash")

    if point is None:
        raise HTTPException(status_code=404, detail="Article not found")

    point_with_vector = client.retrieve(
        collection_name=COLLECTION_NAME,
        ids=[point.id],
        with_vectors=True,
    )
    if not point_with_vector:
        raise HTTPException(status_code=404, detail="Article vector not found")

    ref_vector = point_with_vector[0].vector
    ref_payload = point_with_vector[0].payload
    ref_timestamp = ref_payload.get("pub_timestamp")

    if ref_timestamp is None:
        logger.warning("[SIMILAR] Reference article missing pub_timestamp")
        return []

    min_timestamp = ref_timestamp - (max_days * 24 * 3600)
    max_timestamp = ref_timestamp + (max_days * 24 * 3600)

    filter_condition = models.Filter(
        must=[
            models.FieldCondition(
                key="pub_timestamp",
                range=models.Range(gte=min_timestamp, lte=max_timestamp),
            )
        ]
    )

    query_response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=ref_vector,
        query_filter=filter_condition,
        limit=limit + 1,
        score_threshold=min_similarity,
        with_payload=True,
        with_vectors=False,
    )
    results = query_response.points

    filtered_results = [hit for hit in results if hit.id != point.id]
    filtered_results = filtered_results[:limit]

    similar_articles = []

    feed_hashes = list(set(
        hit.payload.get("feed_sha256")
        for hit in filtered_results
        if hit.payload.get("feed_sha256")
    ))
    feeds_info = {}
    if feed_hashes:
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
            finally:
                cursor.close()

    for hit in filtered_results:
        article = hit.payload.copy()
        article["item_id"] = hit.id
        article["similarity_score"] = hit.score

        f_hash = article.get("feed_sha256")
        if f_hash in feeds_info:
            article["feed_title"] = feeds_info[f_hash]["feed_title"]
            article["feed_icon"] = feeds_info[f_hash]["feed_icon"]

        article.pop("pub_timestamp", None)
        similar_articles.append(article)

    logger.info("[SIMILAR] Found %d similar articles", len(similar_articles))
    return similar_articles