from database.init_db import get_db


def user(user, feedsha256):

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM user_subscriptions WHERE user_id = %s AND feed_sha256 = %s",
            (user["id"], feedsha256),
        )
        result = cursor.fetchone()
        status = "Subscribed" if result else "Not subscribed"
        return {"user_feed_subscription": status}