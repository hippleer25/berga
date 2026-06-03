import logging

import requests
from readability import Document
from urllib.parse import urljoin, urlparse

from database.init_db import get_db
from intelligence.embeddings import get_qdrant_client, COLLECTION_NAME
from intelligence.similar import get_similar_articles
from i18n.locale_map import accept_language_header

logger = logging.getLogger(__name__)

FIREFOX_UA = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"


def _base_headers() -> dict:
    return {
        "User-Agent": FIREFOX_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": accept_language_header(),
    }


_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(_base_headers())
    return _session


def _refresh_session_locale() -> None:
    global _session
    if _session is not None:
        _session.headers["Accept-Language"] = accept_language_header()


def _resolve_images(html: str, base_url: str) -> str:
    from lxml import html as lxml_html
    from lxml import etree

    tree = lxml_html.fromstring(html)

    for img in tree.iter("img"):
        src = img.get("src") or img.get("data-src")
        if src:
            img.set("src", urljoin(base_url, src))
        for attr in ["width", "height", "style"]:
            if attr in img.attrib:
                del img.attrib[attr]

    return etree.tostring(tree, encoding="unicode", method="html")


def _clean_html(html: str) -> str:
    from lxml import html as lxml_html
    from lxml import etree

    tree = lxml_html.fromstring(html)

    unwrap_tags = {"u", "ins", "mark", "s", "strike", "del"}

    for element in tree.iter():
        if element.tag in unwrap_tags:
            element.drop_tag()
            continue

        style = element.get("style")
        if style:
            new_style = ";".join(
                part for part in style.split(";")
                if not part.strip().lower().startswith("text-decoration")
            )
            if new_style:
                element.set("style", new_style)
            else:
                del element.attrib["style"]

    return etree.tostring(tree, encoding="unicode", method="html")


def _get_interaction_status(user_id: int, item_id: str) -> dict:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT action FROM interactions WHERE user_id = %s AND item_id = %s",
                (user_id, item_id),
            )
            actions = {row["action"] for row in cursor.fetchall()}
        finally:
            cursor.close()
    return {
        "liked": "like" in actions,
        "disliked": "dislike" in actions,
        "saved": "saved" in actions,
    }


def get(user_id: int, item_id: str):
    client = get_qdrant_client()
    result = client.retrieve(
        collection_name=COLLECTION_NAME,
        ids=[item_id],
        with_payload=True,
    )

    if not result:
        return None

    payload = result[0].payload
    feed_title = payload.get("feed_title", "")
    author = payload.get("author", "")
    feed_icon = payload.get("feed_icon", "")
    pub_date = payload.get("pub_date", "")
    url = payload.get("link", "")
    feed_sha256 = payload.get("feed_sha256", "")

    similar_articles = []
    try:
        similar_raw = get_similar_articles(item_id, limit=5, min_similarity=0.5)
        for sim in similar_raw:
            if not isinstance(sim, dict):
                continue
            sim_id = sim.get("item_id", "")
            if sim_id == item_id:
                continue
            similar_articles.append({
                "item_id": sim_id,
                "title": sim.get("title", "Untitled"),
                "link": sim.get("link", "#"),
                "feed_title": sim.get("feed_title", ""),
                "feed_icon": sim.get("feed_icon", ""),
                "similarity_score": sim.get("similarity_score", 0.0),
            })
            if len(similar_articles) >= 4:
                break
    except Exception as e:
        logger.warning("[reader] error fetching similar articles: %s", e)

    try:
        _refresh_session_locale()
        session = _get_session()
        response = session.get(url, timeout=15)
        response.raise_for_status()

        doc = Document(response.text)
        content_html = _resolve_images(doc.summary(), url)
        content_html = _clean_html(content_html)

        return {
            "url": url,
            "title": doc.title(),
            "feed_title": feed_title,
            "author": author,
            "feed_icon": feed_icon,
            "pub_date": pub_date,
            "feed_sha256": feed_sha256,
            "content_html": content_html,
            "similar_articles": similar_articles,
            **_get_interaction_status(user_id, item_id),
        }

    except Exception as e:
        logger.error("[reader] error fetching %s: %s", url, e)

        fallback = {
            "url": url,
            "title": payload.get("title", ""),
            "feed_title": feed_title,
            "author": author,
            "feed_icon": feed_icon,
            "pub_date": pub_date,
            "feed_sha256": feed_sha256,
            "content_html": "",
            "similar_articles": similar_articles,
            **_get_interaction_status(user_id, item_id),
        }
        return fallback
