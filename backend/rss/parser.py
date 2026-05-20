import asyncio
import hashlib
import ipaddress
import logging
import os
import socket
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urlparse

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

FEED_FETCH_TIMEOUT = int(os.getenv("FEED_FETCH_TIMEOUT", "15"))
FEED_PARSER_MAX_WORKERS = int(os.getenv("FEED_PARSER_MAX_WORKERS", "10"))

_executor = ThreadPoolExecutor(max_workers=FEED_PARSER_MAX_WORKERS)

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
]


def _is_private_ip(hostname: str) -> bool:
    """Check if a hostname resolves to a private/internal IP."""
    try:
        ip = ipaddress.ip_address(hostname)
        return any(ip in net for net in _BLOCKED_NETWORKS)
    except ValueError:
        try:
            results = socket.getaddrinfo(hostname, None)
            return any(
                ipaddress.ip_address(addr[4][0]) in _BLOCKED_NETWORKS
                for addr in results
                if addr[0] == socket.AF_INET
            )
        except (socket.gaierror, IndexError):
            return False


def _validate_feed_url(url: str) -> bool:
    """Reject URLs pointing to internal/private addresses (SSRF protection)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    if hostname in ("localhost",):
        return False
    if _is_private_ip(hostname):
        return False
    return True

async def fetch_feed_content(session: aiohttp.ClientSession, feed_url: str) -> str:
    timeout = aiohttp.ClientTimeout(total=FEED_FETCH_TIMEOUT)
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
    if not _validate_feed_url(feed_url):
        return {
            "feed_url": feed_url,
            "result": {"status": "error", "message": "Feed URL rejected: internal/private address not allowed"},
        }
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
