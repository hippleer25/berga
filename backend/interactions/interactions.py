from database.init_db import get_db
from interactions.profile_updater import interact as _interact


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
    return _interact(user_id, item_id, "saved")


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
            values = []
            for item_id in item_ids:
                values.extend([user_id, item_id, 'view'])
            placeholders = ','.join(['(%s, %s, %s, NOW())'] * len(item_ids))
            query = f"""
                INSERT INTO interactions (user_id, item_id, action, created_at)
                VALUES {placeholders}
                ON DUPLICATE KEY UPDATE created_at = NOW()
            """
            cursor.execute(query, values)

            ids_placeholder = ','.join(['%s'] * len(item_ids))
            cursor.execute(f"""
                UPDATE article_stats
                SET views_count = views_count + 1
                WHERE item_id IN ({ids_placeholder})
            """, item_ids)

            conn.commit()
            return {"status": "success", "message": f"{len(item_ids)} views registered"}
        except Exception as e:
            conn.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            cursor.close()