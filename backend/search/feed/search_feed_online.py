from ddgs import DDGS
from urllib.parse import urlparse
from i18n.locale_map import ddg_region
import logging

logger = logging.getLogger(__name__)

# The "duckduckgo" backend is frequently blocked server-side ("No results found"
# for every query). "auto" rotates providers; explicit fallbacks on top of it.
_BACKENDS = ("auto", "brave", "bing")

BLACKLIST = {
    "wikipedia.org",
    "news.google.com",
    "google.com",
    "reddit.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "youtube.com",
    "amazon.com",
}

def score_result(r: dict) -> int:
    score = 0
    parsed = urlparse(r["href"])
    path = parsed.path.strip("/")

    domain = parsed.netloc.replace("www.", "")
    if any(domain.endswith(b) for b in BLACKLIST):
        return -1

    if path == "":
        score += 10
    elif len(path.split("/")) <= 2:
        score += 5

    if parsed.scheme == "https":
        score += 2

    return score

def discover_online(query: str):
    try:
        return _ddg_search(query)
    except Exception as e:
        logger.warning("[FEED-DISCOVER] online search failed for %r: %s", query, e)
        return []

async def discover_site_feeds_via_search(url: str, max_pages: int = 3) -> list:
    """Fallback for SPA / bot-guarded sites whose homepage exposes no feed links:
    search the web for pages on the domain that list its feeds (e.g. an RSS
    directory page) and extract the feed URLs from those pages."""
    from search.feed.search_feed_urls import feeds as find_feed_urls

    domain = urlparse(url).netloc.replace("www.", "")
    if not domain:
        return []

    pages = discover_online(f"site:{domain} rss feed")
    found: list = []
    for page in pages[:max_pages]:
        try:
            page_feeds = await find_feed_urls(page["url"], crawl_depth=0)
            found.extend(f for f in page_feeds if f not in found)
        except Exception as e:
            logger.warning("[FEED-DISCOVER] fallback crawl failed for %s: %s", page["url"], e)
    if found:
        logger.info("[FEED-DISCOVER] search fallback found %d feeds for %s", len(found), domain)
    return found

def _ddg_search(query: str):
    results = None
    for backend in _BACKENDS:
        try:
            results = DDGS().text(
                query,
                region=ddg_region(),
                safesearch='off',
                timelimit=None,
                max_results=10,
                backend=backend
            )
        except Exception as e:
            logger.warning("[FEED-DISCOVER] backend=%s failed for %r: %s", backend, query, e)
            results = None
            continue
        if results:
            break

    if not results:
        return []

    scored = [
        {"title": r["title"], "url": r["href"], "score": score_result(r)}
        for r in results
    ]

    scored = sorted(
        [r for r in scored if r["score"] >= 0],
        key=lambda x: x["score"],
        reverse=True
    )

    return scored
