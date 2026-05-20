import hashlib
import logging

import listparser
from fastapi import HTTPException
from database.init_db import get_db

logger = logging.getLogger(__name__)


def _get_or_create_folder(
    cursor, user_id: int, username: str, name: str, parent_id: str | None
) -> str:
    folder_sha256 = hashlib.sha256(
        f"{username}^{parent_id or ''}^{name}".encode()
    ).hexdigest()

    cursor.execute("SELECT id FROM folders WHERE id = %s", (folder_sha256,))
    if cursor.fetchone():
        return folder_sha256

    cursor.execute("""
        INSERT IGNORE INTO folders (id, user_id, name, parent_id)
        VALUES (%s, %s, %s, %s)
    """, (folder_sha256, user_id, name, parent_id))

    return folder_sha256


def _resolve_folder_chain(
    cursor, user_id: int, username: str, tags: list[str]
) -> str | None:
    if not tags:
        return None

    parent_id = None
    for name in tags:
        parent_id = _get_or_create_folder(cursor, user_id, username, name, parent_id)
    return parent_id


def _import_feed(
    cursor, user: dict, feed_url: str, feed_title: str, tags: list[str]
) -> dict:
    feed_sha256 = hashlib.sha256(feed_url.encode()).hexdigest()
    user_id = user["id"]
    username = user["username"]

    cursor.execute("""
        INSERT IGNORE INTO feeds (feed_sha256, feed_url, feed_title)
        VALUES (%s, %s, %s)
    """, (feed_sha256, feed_url, feed_title or None))

    cursor.execute("""
        INSERT IGNORE INTO user_subscriptions (user_id, feed_sha256)
        VALUES (%s, %s)
    """, (user_id, feed_sha256))

    cursor.execute("""
        UPDATE feeds
        SET total_users = (
            SELECT COUNT(*) FROM user_subscriptions WHERE feed_sha256 = %s
        )
        WHERE feed_sha256 = %s
    """, (feed_sha256, feed_sha256))

    folder_id = _resolve_folder_chain(cursor, user_id, username, tags)
    if folder_id is not None:
        cursor.execute("""
            INSERT IGNORE INTO feed_folders (user_id, feed_sha256, folder_id)
            VALUES (%s, %s, %s)
        """, (user_id, feed_sha256, folder_id))

    for tag in tags:
        cursor.execute("""
            INSERT IGNORE INTO feed_tags (user_id, feed_sha256, tag)
            VALUES (%s, %s, %s)
        """, (user_id, feed_sha256, tag))

    return {"url": feed_url, "title": feed_title, "folder_id": folder_id, "tags": tags}


async def receive(content: bytes, user: dict):
    result = listparser.parse(content.decode("utf-8"))

    if not result.feeds and result.bozo:
        raise HTTPException(status_code=400, detail="Invalid or malformed OPML file")

    if not result.feeds:
        return {"imported": 0, "feeds": []}

    with get_db() as conn:
        cursor = conn.cursor()
        imported = []

        try:
            for feed in result.feeds:
                if not feed.url:
                    continue

                entry = _import_feed(
                    cursor=cursor,
                    user=user,
                    feed_url=feed.url,
                    feed_title=feed.title or "",
                    tags=feed.tags or [],
                )
                imported.append(entry)

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Import failed: {e}")
        finally:
            cursor.close()

    logger.info("Imported %d feeds for user %s", len(imported), user["id"])

    return {"imported": len(imported), "feeds": imported}
