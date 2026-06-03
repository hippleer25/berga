from database.init_db import get_db
from feed import check_subscription


def get_all(feed_sha256, user):
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM feeds WHERE feed_sha256 = %s",
                (feed_sha256,),
            )
            feed = cursor.fetchone()
            if not feed:
                return None

            subscription = check_subscription.user(user, feed_sha256)
            return {**feed, **subscription}
        finally:
            cursor.close()