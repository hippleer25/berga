import hashlib
import json
import logging

from database.init_db import get_db
from database.qdrant_utils import refresh_publisher_freq
from intelligence.recommendations import invalidate_cache, invalidate_interaction_cache

logger = logging.getLogger(__name__)


def unsubscribe(user, feed_url):
    logger.info("Unsubscribing user %s from %s", user["id"], feed_url)

    feed_sha256 = hashlib.sha256(feed_url.encode()).hexdigest()

    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                DELETE FROM user_subscriptions WHERE user_id = %s AND feed_sha256 = %s
            """, (user["id"], feed_sha256))

            if cursor.rowcount == 0:
                return {"status": "error", "message": "Subscription could not be found"}

            cursor.execute("""
                UPDATE feeds
                SET total_users = (
                    SELECT COUNT(*) FROM user_subscriptions WHERE feed_sha256 = %s
                )
                WHERE feed_sha256 = %s
            """, (feed_sha256, feed_sha256))

            cursor.execute("""
                DELETE FROM feed_folders WHERE user_id = %s AND feed_sha256 = %s
            """, (user["id"], feed_sha256))

            cursor.execute("""
                SELECT feed_sha256 FROM user_subscriptions WHERE user_id = %s
            """, (user["id"],))
            remaining = [row[0] for row in cursor.fetchall()]

            cursor.execute("""
                SELECT publisher_likes, publisher_dislikes FROM user_vectors WHERE user_id = %s
            """, (user["id"],))
            vec_row = cursor.fetchone()
            if vec_row:
                pub_likes = json.loads(vec_row[0]) if vec_row[0] else {}
                pub_dislikes = json.loads(vec_row[1]) if vec_row[1] else {}
                changed = False
                if feed_sha256 in pub_likes:
                    del pub_likes[feed_sha256]
                    changed = True
                if feed_sha256 in pub_dislikes:
                    del pub_dislikes[feed_sha256]
                    changed = True
                if changed:
                    cursor.execute("""
                        UPDATE user_vectors
                        SET publisher_likes = %s, publisher_dislikes = %s
                        WHERE user_id = %s
                    """, (json.dumps(pub_likes), json.dumps(pub_dislikes), user["id"]))

            conn.commit()

            refresh_publisher_freq(user["id"], remaining)
            invalidate_cache(user["id"])
            invalidate_interaction_cache(user["id"])

            return {"status": "success", "message": "Feed removido com sucesso"}

        except Exception as e:
            conn.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            cursor.close()
