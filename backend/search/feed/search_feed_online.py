from ddgs import DDGS
from ddgs.exceptions import DDGSException
from urllib.parse import urlparse
from i18n.locale_map import ddg_region
import logging

logger = logging.getLogger(__name__)

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
	except DDGSException:
		return []

def _ddg_search(query: str):
    results = DDGS().text(
        query,
        region=ddg_region(),
        safesearch='off',
        timelimit=None,
        max_results=10,
        backend="duckduckgo"
    )

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