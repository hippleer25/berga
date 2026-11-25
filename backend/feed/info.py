from database.init_db import get_db
from feed import check_subscription


def get_all(feed_sha256, user):
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT f.*, COALESCE(ufo.custom_title, f.feed_title) AS feed_title
                FROM feeds f
                LEFT JOIN user_feed_overrides ufo
                  ON ufo.user_id = %s AND ufo.feed_sha256 = f.feed_sha256
                WHERE f.feed_sha256 = %s
                """,
                (user["id"], feed_sha256),
            )
            feed = cursor.fetchone()
            if not feed:
                return None

            subscription = check_subscription.user(user, feed_sha256)
            result = {**feed, **subscription}

            # Current manual publisher boost for this user (weights in [0, 1]
            # per direction; absent map means "no manual boost").
            from intelligence.affinity import get_publisher_boosts

            boost = get_publisher_boosts(user["id"]).get(feed_sha256)
            result["publisher_boost"] = boost or {"positive": 0.0, "negative": 0.0}
            return result
        finally:
            cursor.close()