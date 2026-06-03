import hashlib
import logging

from database.init_db import get_db
from database.qdrant_utils import refresh_publisher_freq
from intelligence.recommendations import invalidate_cache

logger = logging.getLogger(__name__)


def subscribe(user, feed_url):
    logger.info("Subscribing user %s to %s", user["id"], feed_url)

    feed_sha256 = hashlib.sha256(feed_url.encode()).hexdigest()

    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT IGNORE INTO feeds (feed_sha256, feed_url)
                VALUES (%s, %s)
            """, (feed_sha256, feed_url))

            cursor.execute("""
                INSERT IGNORE INTO user_subscriptions (user_id, feed_sha256)
                VALUES (%s, %s)
            """, (user["id"], feed_sha256))

            if cursor.rowcount == 0:
                return {"status": "info", "message": "User already following the account"}

            cursor.execute("""
                UPDATE feeds
                SET total_users = (
                    SELECT COUNT(*) FROM user_subscriptions WHERE feed_sha256 = %s
                )
                WHERE feed_sha256 = %s
            """, (feed_sha256, feed_sha256))

            conn.commit()

            cursor.execute("""
                SELECT feed_sha256 FROM user_subscriptions WHERE user_id = %s
            """, (user["id"],))
            current = [row[0] for row in cursor.fetchall()]

            refresh_publisher_freq(user["id"], current)
            invalidate_cache(user["id"])

            return {"status": "success", "message": "Feed added successfully"}

        except Exception as e:
            conn.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            cursor.close()
