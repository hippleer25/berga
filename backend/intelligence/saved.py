from typing import Optional

from database.init_db import get_db
from intelligence.embeddings import get_qdrant_client, COLLECTION_NAME
from intelligence.recents import _resolve_feed_filter, _enrich_with_feed_metadata


def get_saved(
    user_id: int,
    limit: int = 20,
    page: int = 0,
    folder_id: Optional[str] = None,
    feed_sha256: Optional[str] = None,
) -> list[dict]:
    feed_filter = _resolve_feed_filter(user_id, folder_id, feed_sha256)

    if feed_filter is not None and len(feed_filter) == 0:
        return []

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT item_id FROM interactions
                WHERE user_id = %s AND action = 'saved'
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, limit, page * limit),
            )
            rows = cursor.fetchall()
        finally:
            cursor.close()

    if not rows:
        return []

    item_ids = [str(row["item_id"]) for row in rows]

    client = get_qdrant_client()
    points = client.retrieve(
        collection_name=COLLECTION_NAME,
        ids=item_ids,
        with_payload=True,
        with_vectors=False,
    )

    id_to_point = {str(p.id): p for p in points}

    feed_set = set(feed_filter) if feed_filter is not None else None
    results: list[dict] = []
    for item_id in item_ids:
        point = id_to_point.get(item_id)
        if point is None:
            continue
        if feed_set is not None and point.payload.get("feed_sha256") not in feed_set:
            continue
        item = point.payload.copy()
        item["item_id"] = str(point.id)
        item["relevance_score"] = 0.0
        item["saved"] = True
        results.append(item)

    _enrich_with_feed_metadata(results)
    return results
