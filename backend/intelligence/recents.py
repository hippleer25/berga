from datetime import datetime, timedelta, timezone
from typing import Optional

from database.init_db import get_db
from intelligence.embeddings import get_qdrant_client, COLLECTION_NAME
from qdrant_client.http import models


def _resolve_feed_filter(
    user_id: int,
    folder_id: Optional[str],
    feed_sha256: Optional[str],
) -> Optional[list[str]]:
    feeds: set[str] = set()

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
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
                    SELECT feed_sha256 FROM user_subscriptions
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
        finally:
            cursor.close()

    return list(feeds) if feeds else []


# ------------------------------------------------------------------
# Filtro Qdrant
# ------------------------------------------------------------------

def _build_qdrant_filter(max_days: int, feed_filter: Optional[list[str]]) -> models.Filter:
    min_timestamp = (datetime.now(timezone.utc) - timedelta(days=max_days)).timestamp()

    must_conditions = [
        models.FieldCondition(
            key="pub_timestamp",
            range=models.Range(gte=min_timestamp),
        )
    ]

    if feed_filter is not None:
        must_conditions.append(
            models.FieldCondition(
                key="feed_sha256",
                match=models.MatchAny(any=feed_filter),
            )
        )

    return models.Filter(must=must_conditions)


# ------------------------------------------------------------------
# Enrichment with feed metadata
# ------------------------------------------------------------------

def _enrich_with_feed_metadata(items: list[dict]) -> list[dict]:
    """Fetches feed_title and feed_icon from MySQL and enriches the items."""
    if not items:
        return items

    feed_hashes = list(set(
        item.get("feed_sha256") for item in items if item.get("feed_sha256")
    ))
    if not feed_hashes:
        return items

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

    for item in items:
        f_hash = item.get("feed_sha256")
        if f_hash and f_hash in feeds_info:
            item["feed_title"] = feeds_info[f_hash]["feed_title"]
            item["feed_icon"]  = feeds_info[f_hash]["feed_icon"]
            item["feed_link"]  = feeds_info[f_hash]["feed_link"]

    return items


# ------------------------------------------------------------------
# Função principal
# ------------------------------------------------------------------

def get_recents(
    user_id: int,
    limit: int,
    max_days: int,
    folder_id: Optional[str] = None,
    feed_sha256: Optional[str] = None,
    exclude_ids=None,
) -> list[dict]:
    """
    Retorna os artigos mais recentes (limit) publicados nos últimos max_days,
    excluindo os IDs em exclude_ids, com suporte a filtro por pasta ou feed.
    """
    if exclude_ids is None:
        exclude_ids = set()

    feed_filter = _resolve_feed_filter(user_id, folder_id, feed_sha256)

    # Valid filter but no matching feeds → return empty
    if feed_filter is not None and len(feed_filter) == 0:
        return []

    client = get_qdrant_client()
    filter_condition = _build_qdrant_filter(max_days, feed_filter)

    scroll_result = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=filter_condition,
        limit=limit * 3,  # margin for exclusions
        with_payload=True,
        with_vectors=False,
    )[0]

    scroll_result.sort(key=lambda p: p.payload.get("pub_timestamp", 0), reverse=True)

    recentes = []
    for point in scroll_result:
        if point.id in exclude_ids:
            continue
        item = point.payload.copy()
        item["item_id"]         = point.id
        item["relevance_score"] = 0.0
        recentes.append(item)
        if len(recentes) >= limit:
            break

    _enrich_with_feed_metadata(recentes)

    return recentes