from ddgs import DDGS
from urllib.parse import urlparse

# Sites that aggregate/describe news but aren't the source
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
    """Higher = better candidate for an official homepage."""
    score = 0
    parsed = urlparse(r["href"])
    path = parsed.path.strip("/")

    # Penalize blacklisted domains
    domain = parsed.netloc.replace("www.", "")
    if any(domain.endswith(b) for b in BLACKLIST):
        return -1

    # Prefer root or near-root URLs (homepages)
    if path == "":
        score += 10
    elif len(path.split("/")) <= 2:
        score += 5

    # Prefer HTTPS
    if parsed.scheme == "https":
        score += 2

    return score

def discover_online(query: str):
    refined_query = f"{query} official news website"

    results = DDGS().text(
        refined_query,
        region='us-en',
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

    # Filter blacklisted (-1) and sort by score
    scored = sorted(
        [r for r in scored if r["score"] >= 0],
        key=lambda x: x["score"],
        reverse=True
    )

    return scored