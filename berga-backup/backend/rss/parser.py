import asyncio
import hashlib
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import aiohttp
import feedparser
from jose import jwt, JWTError

from auth.token import ALGORITHM, SECRET_KEY
from database.init_db import get_db
from database.qdrant_utils import add_item_to_qdrant
from intelligence.embeddings import (
    embedding_text,
    get_embedding_model,
    get_qdrant_client,
    COLLECTION_NAME,
)

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=10)

async def fetch_feed_content(session: aiohttp.ClientSession, feed_url: str) -> str:
    timeout = aiohttp.ClientTimeout(total=15)
    async with session.get(feed_url, timeout=timeout) as response:
        response.raise_for_status()
        return await response.text()


def parse_and_save_feed(feed_url: str, raw_content: str = None):
    parsed = feedparser.parse(raw_content if raw_content else feed_url)
    feed_sha256 = hashlib.sha256(feed_url.encode()).hexdigest()

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            feed_info = parsed.get("feed", {})
            title_feed = feed_info.get("title", "No title")
            link_feed = feed_info.get("link", feed_url)
            description_feed = feed_info.get("description", "")
            lang_feed = feed_info.get("language", "")
            icon_feed = f"https://www.google.com/s2/favicons?domain={link_feed}&sz=128"

            entries_count = len(parsed.get("entries", []))

            feed_last_update = None
            if "updated_parsed" in feed_info and feed_info.updated_parsed:
                feed_last_update = datetime(*feed_info.updated_parsed[:6])
            elif "published_parsed" in feed_info and feed_info.published_parsed:
                feed_last_update = datetime(*feed_info.published_parsed[:6])

            cursor.execute("""
            UPDATE feeds
            SET feed_title = %s,
                feed_link = %s,
                feed_description = %s,
                feed_lang = %s,
                feed_icon = %s,
                feed_last_update = %s,
                entries_count = %s,
                last_parsed_at = NOW(),
                parsed = parsed + 1
            WHERE feed_sha256 = %s
            """, (
                title_feed, link_feed, description_feed,
                lang_feed, icon_feed, feed_last_update,
                entries_count, feed_sha256
            ))

            get_embedding_model()
            get_qdrant_client()

            for entry in parsed.get("entries", []):
                link = entry.get("link", "")
                if not link:
                    continue

                title = entry.get("title", "").strip()
                description = entry.get("description", "").strip()
                author = entry.get("author", "").strip()

                if not title:
                    continue

                item_id = str(uuid.uuid5(uuid.NAMESPACE_URL, link))
                old_hash = hashlib.sha256(link.encode()).hexdigest()

                pub_date = pub_timestamp = None
                for date_field in ("published_parsed", "updated_parsed"):
                    value = entry.get(date_field)
                    if value:
                        pub_date = datetime(*value[:6])
                        pub_timestamp = pub_date.timestamp()
                        break

                vector = embedding_text(title)
                logger.debug("[parser] %sd vector — %s", f"{len(vector)}d", title[:80])

                payload = {
                    "title": title,
                    "description": description,
                    "author": author,
                    "link": link,
                    "pub_date": pub_date.isoformat() if pub_date else None,
                    "pub_timestamp": pub_timestamp,
                    "feed_sha256": feed_sha256,
                    "feed_title": title_feed,
                    "feed_icon": icon_feed,
                    "url_hash": old_hash,
                }

                add_item_to_qdrant(item_id, vector, payload)

            conn.commit()
            return {
                "status": "success",
                "message": f"Feed {feed_sha256} processed with {entries_count} items.",
            }

        except Exception as e:
            conn.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            cursor.close()


async def parse_and_save_feed_async(
    session: aiohttp.ClientSession,
    feed_url: str,
) -> dict:
    try:
        raw_content = await fetch_feed_content(session, feed_url)
    except Exception as e:
        return {
            "feed_url": feed_url,
            "result": {"status": "error", "message": f"Fetch failed: {e}"},
        }

    result = await asyncio.get_running_loop().run_in_executor(
        _executor,
        parse_and_save_feed,
        feed_url,
        raw_content,
    )
    return {"feed_url": feed_url, "result": result}


def process_feed_with_auth(token: str, feed_url: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") is None:
            return {"status": "error", "message": "Token inválido"}
        return parse_and_save_feed(feed_url)
    except JWTError:
        return {"status": "error", "message": "Token inválido"}
