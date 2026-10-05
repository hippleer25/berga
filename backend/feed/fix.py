"""
feed/fix.py — broken-feed repair flow.

1. diagnose(): regex pre-classification of the persisted last_error, refined
   by an optional LLM pass (ROUTING tier, strict JSON).
2. find_candidates(): re-discover RSS/Atom URLs for the feed's site —
   vendored feedfinder link-sniffing, DDG web-search fallback and origin
   path variants — then live-validate every candidate (fetch + feedparser,
   must yield content) before it's shown to the user.
3. apply(): hands the chosen URL to _edit_feed_url (preserves folder/tags/
   custom rename and triggers a fresh parse).
"""

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse

import aiohttp
import feedparser
from fastapi import HTTPException

from database.init_db import get_db
from rss.parser import _validate_feed_url, _feed_fetch_headers

logger = logging.getLogger(__name__)

# ── Diagnosis ─────────────────────────────────────────────────────────────────

DiagnosticCodes = (
    "MOVED_GONE", "DNS_GONE", "TIMEOUT", "CONNECT_FAIL", "SSL_ERROR",
    "AUTH_REQUIRED", "RATE_LIMITED", "NOT_RSS", "UNKNOWN",
)

_DIAGNOSIS_PATTERNS: tuple[tuple[str, tuple[str, ...], int | None], ...] = (
    ("RATE_LIMITED", (r"HTTP 429", r"429:", r"got 429"), 429),
    ("AUTH_REQUIRED", (r"HTTP 40[137]", r"got 40[137]"), None),
    ("MOVED_GONE", (r"HTTP 404", r"HTTP 410", r"got 404", r"got 410"), 404),
    ("DNS_GONE", (
        r"gaierror", r"ENOTFOUND", r"name or service not known",
        r"temporarily failure in name resolution", r"nodename nor servname",
        r"cannot resolve", r"no address associated",
    ), None),
    ("TIMEOUT", (r"timed? ?out", r"timeout", r"deadline exceeded"), None),
    ("CONNECT_FAIL", (r"connection refused", r"connection reset", r"unreachable", r"connect error", r"proxyerror", r"truncated"), None),
    ("SSL_ERROR", (r"ssl", r"certificate", r"certificat", r"handshake"), None),
    ("NOT_RSS", (
        r"cannot parse", r"not (?:a |an )?(?:valid )?(?:feed|rss|xml)", r"strict feed parser",
        r"bozo", r"is not recognized", r"no (?:feed|entries)", r"syntax error", r"invalid token",
    ), None),
)

_STATUS_HINT = {404: "MOVED_GONE", 410: "MOVED_GONE", 401: "AUTH_REQUIRED",
                403: "AUTH_REQUIRED", 429: "RATE_LIMITED"}


def _regex_diagnose(last_error: str | None, http_status: int | None) -> str:
    if http_status and http_status in _STATUS_HINT:
        return _STATUS_HINT[http_status]
    text = (last_error or "").lower()
    if not text:
        return "UNKNOWN"
    for code, patterns, _ in _DIAGNOSIS_PATTERNS:
        if any(re.search(p, text) for p in patterns):
            return code
    return "UNKNOWN"


def _llm_diagnose(last_error: str, http_status: int | None) -> dict | None:
    """Refine the regex guess with a cheap LLM pass. Never raises."""
    try:
        from mota.ai_lib import generate_text

        prompt = (
            "An RSS reader failed to fetch/parse a feed. Classify the failure.\n"
            f"HTTP status: {http_status or 'none'}\n"
            f"Last error: {last_error[:400]}\n"
            "Choose exactly one code from: MOVED_GONE (404/410, domain dead or "
            "feed relocated), DNS_GONE (name resolution), TIMEOUT, CONNECT_FAIL, "
            "SSL_ERROR, AUTH_REQUIRED (401/403), RATE_LIMITED (429), "
            "NOT_RSS (URL answers but with no feed content), UNKNOWN.\n"
            "Reply with strict JSON only: {\"code\": \"<CODE>\", \"reason\": \"<=20 words\"}"
        )
        raw = generate_text(
            prompt,
            system_prompt="You are a precise JSON-only classifier.",
            max_tokens=200,
            usage="routing",
        )
        if not raw:
            return None
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group(0))
        code = str(data.get("code", "")).upper().strip()
        if code not in DiagnosticCodes:
            return None
        return {"code": code, "reason": str(data.get("reason", ""))[:200], "source": "llm"}
    except Exception:
        logger.warning("LLM diagnose failed", exc_info=True)
        return None


def diagnose(feed_row: dict) -> dict:
    code = _regex_diagnose(feed_row.get("last_error"), feed_row.get("last_http_status"))
    result = {"code": code, "reason": (feed_row.get("last_error") or "")[:200], "source": "regex"}
    if code in ("UNKNOWN", "NOT_RSS", "MOVED_GONE") and feed_row.get("last_error"):
        refined = _llm_diagnose(feed_row["last_error"], feed_row.get("last_http_status"))
        if refined:
            result = refined
    return result


# ── Candidate discovery ────────────────────────────────────────────────────────

_COMMON_FEED_PATHS = (
    "feed", "feed/", "rss", "rss/", "feed.xml", "rss.xml", "atom.xml",
    "index.xml", "index.rss", "atom", "feeds", "blog/feed", "blog/feed/",
    "wp-rss2.php", "news/feed", "feeds/latest",
)

# Query-string feed forms used by WordPress/FeedBurner sites.
_QUERY_VARIANTS = ("?feed=rss2", "?feed=atom", "?feed=rss", "?feed=rss2&cat=-1")

# Candidate validation budget — the modal waits on this, keep it snappy.
_VALIDATE_TIMEOUT = int(os.getenv("FEED_FIX_VALIDATE_TIMEOUT", "8"))
_MAX_CANDIDATES = int(os.getenv("FEED_FIX_MAX_CANDIDATES", "18"))


def _site_origin(url: str | None) -> str | None:
    """scheme://netloc of a URL (no path/query), or None."""
    if not url:
        return None
    parsed = urlparse(url if "//" in str(url) else f"https://{url}")
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


def _site_variants(feed_url: str, feed_link: str | None) -> list[str]:
    """
    Origin-root + common feed path guesses derived from the known URLs.
    Crucially, guesses are anchored on the *origin* — never on a dead feed
    path (e.g. /rss2.xml → 404).
    """
    urls: list[str] = []
    origins: list[str] = []

    for raw in (feed_link, feed_url):
        origin = _site_origin(raw)
        if origin and origin not in origins:
            origins.append(origin)

    for origin in origins:
        urls.append(origin)
        for query in _QUERY_VARIANTS:
            urls.append(f"{origin}/{query}")
        for path in _COMMON_FEED_PATHS:
            urls.append(f"{origin}/{path}")
    return list(dict.fromkeys(urls))


async def _discover_via_page(base_url: str, via_search: bool) -> list[str]:
    found: list[str] = []
    try:
        from search.feed.search_feed_urls import feeds as find_feed_urls

        found.extend(await find_feed_urls(base_url, crawl_depth=1, max_pages_per_site=8))
    except Exception:
        logger.warning("[FIX] feedfinder discovery failed for %s", base_url, exc_info=True)

    if not found and via_search:
        try:
            from search.feed.search_feed_online import discover_site_feeds_via_search

            found.extend(await discover_site_feeds_via_search(base_url))
        except Exception:
            logger.warning("[FIX] web-search discovery failed for %s", base_url, exc_info=True)

    return list(dict.fromkeys(found))


async def _validate_candidate(session: aiohttp.ClientSession, url: str) -> dict | None:
    """Fetch + parse a candidate; None unless it presents real feed content."""
    if not _validate_feed_url(url):
        return None
    try:
        timeout = aiohttp.ClientTimeout(total=_VALIDATE_TIMEOUT)
        async with session.get(url, timeout=timeout, headers=_feed_fetch_headers()) as resp:
            if resp.status >= 400:
                return None
            content_type = resp.headers.get("Content-Type", "")
            status = resp.status
            raw = await resp.read()
        if len(raw) < 512:
            return None

        def _parse() -> dict:
            parsed = feedparser.parse(raw, request_headers={"User-Agent": _feed_fetch_headers()["User-Agent"]})
            feed_info = parsed.get("feed") or {}
            entries = parsed.get("entries") or []
            last_title = ""
            last_pub = None
            if entries:
                last_title = (entries[0].get("title") or "").strip()
                stamp = entries[0].get("published_parsed") or entries[0].get("updated_parsed")
                if stamp:
                    try:
                        last_pub = datetime(*stamp[:6], tzinfo=timezone.utc).date().isoformat()
                    except (TypeError, ValueError, OverflowError):
                        last_pub = None
            return {
                "title": (feed_info.get("title") or "").strip(),
                "entries": len(entries),
                "last_title": last_title,
                "last_pub": last_pub,
            }

        info = await asyncio.get_running_loop().run_in_executor(None, _parse)
        if not info["title"] and info["entries"] == 0:
            return None

        hostname = urlparse(url).netloc
        score = 20 + info["entries"]
        if url.startswith("https://"):
            score += 2
        if content_type.startswith(("application/rss+xml", "application/atom+xml", "application/xml", "text/xml")):
            score += 10
        return {"url": url, "title": info["title"], "entries": info["entries"],
                "last_title": info["last_title"], "last_pub": info["last_pub"],
                "http_status": status, "hostname": hostname, "score": score}
    except Exception:
        return None


async def find_candidates(feed_url: str, feed_link: str | None = None) -> list[dict]:
    """
    Discover + validate candidate feed URLs for a broken feed, ranked best
    first. Pure discovery — no DB writes, nothing applied automatically.

    Discovery is anchored on the site *origin* (homepage/feed_link), never on
    the dead feed path — crawling `…/rss2.xml` (404) yields nothing.
    """
    started = time.perf_counter()
    base = _site_origin(feed_link) or _site_origin(feed_url) or feed_url
    discovered = await _discover_via_page(base, via_search=True)
    guessed = _site_variants(feed_url, feed_link)

    candidates_urls = list(dict.fromkeys(discovered + guessed + [feed_url]))
    candidates_urls = candidates_urls[:_MAX_CANDIDATES]

    semaphore = asyncio.Semaphore(4)

    async def check(url: str) -> dict | None:
        async with semaphore:
            return await _validate_candidate(session, url)

    async with aiohttp.ClientSession() as session:
        validated = await asyncio.gather(*(check(u) for u in candidates_urls))
    candidates = [c for c in validated if c]

    # Rank: same-hostname as original site first, then discovery score.
    try:
        original_host = urlparse(feed_url).netloc.removeprefix("www.")
    except Exception:
        original_host = ""
    for c in candidates:
        if c["hostname"].removeprefix("www.") == original_host:
            c["score"] += 25
    candidates.sort(key=lambda c: (-c["score"], c["url"]))

    for c in candidates:
        c.pop("hostname", None)
        c.pop("score", None)
        c["is_current"] = c["url"] == feed_url

    logger.info(
        "[FIX] %d candidates (of %d attempted) for %s in %.1fs",
        len(candidates), len(candidates_urls), feed_url, time.perf_counter() - started,
    )
    return candidates


# ──DB + orchestration glue ────────────────────────────────────────────────────

def _load_feed_for_user(feed_sha256: str, user_id: int) -> dict:
    """Fetch the feeds row after an ownership check (raises 403/404)."""
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT 1 FROM user_subscriptions WHERE user_id = %s AND feed_sha256 = %s",
                (user_id, feed_sha256),
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Feed not found in your subscriptions")
            cursor.execute(
                "SELECT feed_sha256, feed_url, feed_link, feed_title, last_error, last_http_status "
                "FROM feeds WHERE feed_sha256 = %s",
                (feed_sha256,),
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
    if not row:
        raise HTTPException(status_code=404, detail="Feed not found")
    return row


async def analyze(feed_sha256: str, user_id: int) -> dict:
    """Diagnose + produce validated candidate URLs for a broken feed."""
    row = _load_feed_for_user(feed_sha256, user_id)
    diagnosis = await asyncio.to_thread(diagnose, row)
    candidates = await find_candidates(row["feed_url"], row.get("feed_link"))
    return {
        "feed_sha256": feed_sha256,
        "url": row["feed_url"],
        "title": row["feed_title"],
        "diagnosis": diagnosis,
        "candidates": candidates,
    }


async def apply_new_url(new_url: str, feed_sha256: str, user: dict, request=None) -> dict:
    """
    Delegate the actual swap to structure's edit_feed_url (validates ownership,
    preserves folder/tags/custom title, enqueues a fresh parse).
    """
    from feed.following_structure.structure import following_structure, StructureRequest

    body = StructureRequest(task="edit_feed_url", feed=feed_sha256, feed_url=new_url)
    return await following_structure(body, user, request)
