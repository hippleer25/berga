from database.init_db import get_db
from interactions.profile_updater import interact as _interact
from intelligence.recommendations import invalidate_cache, invalidate_interaction_cache
from post.load import _cache_article


def _fetch_and_cache(item_id: str) -> None:
    try:
        from intelligence.embeddings import get_qdrant_client, COLLECTION_NAME
        client = get_qdrant_client()
        result = client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[item_id],
            with_payload=True,
        )
        if not result:
            return
        url = result[0].payload.get("link", "")
        if not url:
            return
        import requests
        from readability import Document
        from post.load import _get_session, _resolve_images, _clean_html
        session = _get_session()
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        doc = Document(resp.text)
        content_html = _resolve_images(doc.summary(), url)
        content_html = _clean_html(content_html)
        _cache_article(item_id, content_html)
    except Exception:
        pass


def like_article(user_id: int, item_id: str):
    return _interact(user_id, item_id, "like")


def dislike_article(user_id: int, item_id: str):
    return _interact(user_id, item_id, "dislike")


def view_article(user_id: int, item_id: str):
    return _interact(user_id, item_id, "view", update_profile=False)


def read_article(user_id: int, item_id: str):
    """User read the article (click). Lower weight than like."""
    return _interact(user_id, item_id, "read")


def save_article(user_id: int, item_id: str):
    result = _interact(user_id, item_id, "saved")
    if result.get("status") == "success":
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE interactions SET archived = 1 "
                    "WHERE user_id = %s AND item_id = %s AND action = 'saved'",
                    (user_id, item_id),
                )
                conn.commit()
            except Exception:
                conn.rollback()
            finally:
                cursor.close()
        _fetch_and_cache(item_id)
    return result


def unsave_article(user_id: int, item_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                DELETE FROM interactions
                WHERE user_id = %s AND item_id = %s AND action = 'saved'
            """, (user_id, item_id))

            cursor.execute("""
                UPDATE article_stats
                SET saved_count = GREATEST(saved_count - 1, 0)
                WHERE item_id = %s
            """, (item_id,))
            conn.commit()
            return {"status": "success", "message": "Removed from saved"}
        except Exception as e:
            conn.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            cursor.close()


def bulk_view_articles(user_id: int, item_ids: list):
    if not item_ids:
        return {"status": "success", "message": "No items"}

    with get_db() as conn:
        cursor = conn.cursor()
        try:
            ids_placeholder = ','.join(['%s'] * len(item_ids))
            cursor.execute(
                f"SELECT item_id FROM interactions WHERE user_id = %s AND action = 'view' AND item_id IN ({ids_placeholder})",
                [user_id] + list(item_ids),
            )
            already_viewed = {row[0] for row in cursor.fetchall()}
            new_ids = [iid for iid in item_ids if iid not in already_viewed]

            if new_ids:
                values = []
                for item_id in new_ids:
                    values.extend([user_id, item_id, 'view'])
                placeholders = ','.join(['(%s, %s, %s, NOW())'] * len(new_ids))
                cursor.execute(
                    f"INSERT INTO interactions (user_id, item_id, action, created_at) VALUES {placeholders}",
                    values,
                )

                new_placeholder = ','.join(['%s'] * len(new_ids))
                cursor.execute(
                    f"UPDATE article_stats SET views_count = views_count + 1 WHERE item_id IN ({new_placeholder})",
                    list(new_ids),
                )

            conn.commit()
            invalidate_cache(user_id)
            invalidate_interaction_cache(user_id)
            return {"status": "success", "message": f"{len(item_ids)} views registered"}
        except Exception as e:
            conn.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            cursor.close()