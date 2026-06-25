import logging

from database.init_db import get_db

logger = logging.getLogger(__name__)


def get_comment(user_id: int, item_id: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, content_md, created_at, updated_at "
                "FROM article_comments WHERE user_id = %s AND item_id = %s",
                (user_id, item_id),
            )
            row = cursor.fetchone()
            if row:
                row["created_at"] = row["created_at"].isoformat() if row.get("created_at") else None
                row["updated_at"] = row["updated_at"].isoformat() if row.get("updated_at") else None
            return row
        finally:
            cursor.close()


def save_comment(user_id: int, item_id: str, content_md: str) -> dict:
    content_md = content_md.strip()
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO article_comments (user_id, item_id, content_md) "
                "VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE content_md = VALUES(content_md)",
                (user_id, item_id, content_md),
            )
            conn.commit()
            if cursor.lastrowid:
                comment_id = cursor.lastrowid
            else:
                cursor.execute(
                    "SELECT id FROM article_comments WHERE user_id = %s AND item_id = %s",
                    (user_id, item_id),
                )
                comment_id = cursor.fetchone()[0]
            return {"status": "success", "id": comment_id}
        except Exception as e:
            conn.rollback()
            logger.error("Error saving comment: %s", e)
            return {"status": "error", "message": str(e)}
        finally:
            cursor.close()


def delete_comment(user_id: int, item_id: str) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM article_comments WHERE user_id = %s AND item_id = %s",
                (user_id, item_id),
            )
            if cursor.rowcount == 0:
                return {"status": "error", "message": "Comment not found"}
            conn.commit()
            return {"status": "success"}
        except Exception as e:
            conn.rollback()
            logger.error("Error deleting comment: %s", e)
            return {"status": "error", "message": str(e)}
        finally:
            cursor.close()
