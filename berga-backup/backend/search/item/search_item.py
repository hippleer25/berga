import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from fastapi import HTTPException
from database.init_db import get_db
from intelligence.embeddings import get_qdrant_client, embedding_text, COLLECTION_NAME
from qdrant_client.http import models

# ---------------------------------------------------------------------------
# Query parsing
# ---------------------------------------------------------------------------

def parse_query(query: str) -> Tuple[List[str], str]:
    """
    Separates quoted phrases from the free-text part of the query.

    Example:
        'inflação "taxa selic" economia'
        → quoted: ['taxa selic'], remainder: 'inflação economia'
    """
    quoted = re.findall(r'"([^"]+)"', query)
    remainder = re.sub(r'"[^"]+"', "", query).strip()
    return quoted, remainder


def _tokenize(text: str) -> List[str]:
    """
    Language-agnostic tokenizer.
    Extracts Unicode letters-only tokens of 3+ characters and deduplicates them.
    The 3-char minimum naturally excludes the vast majority of stopwords
    (articles, prepositions) across virtually all languages — no language-specific
    lists needed, zero maintenance cost.
    """
    tokens = re.findall(r"[^\W\d_]{3,}", text.lower(), re.UNICODE)
    return list(set(tokens))


def _is_short_query(query: str) -> bool:
    """Returns True when the query is 1–2 meaningful words (name, place, ticker…)."""
    return len(_tokenize(query)) <= 2


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _keyword_boost(payload: dict, query_tokens: List[str]) -> float:
    """
    Adds up to +0.25 to the semantic score based on raw token overlap
    between the query and the article title + description.

    Articles without a description are NOT penalised: we only look at
    whatever text is actually present.
    """
    if not query_tokens:
        return 0.0

    title = payload.get("title", "") or ""
    description = payload.get("description", "") or ""
    haystack_tokens = set(_tokenize(f"{title} {description}"))

    if not haystack_tokens:
        return 0.0

    overlap = sum(1 for t in query_tokens if t in haystack_tokens)
    return 0.25 * (overlap / len(query_tokens))


# ---------------------------------------------------------------------------
# Fallback: pure Qdrant scan with no score threshold
# ---------------------------------------------------------------------------

def _keyword_fallback(
    vector: list,
    query_tokens: List[str],
    limit: int,
    qdrant_filter,
    client,
) -> List[dict]:
    """
    Last-resort search: fetch the top-N nearest vectors from Qdrant with NO
    score threshold, then keep only those whose title or description contain
    at least one query token.

    Stays entirely inside Qdrant — no SQL items table needed.
    Results are tagged with search_type="keyword_fallback".
    """
    if not query_tokens:
        return []

    result = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        query_filter=qdrant_filter,
        limit=max(limit * 10, 100),
        score_threshold=None,
        with_payload=True,
        with_vectors=False,
    )
    hits = result.points

    candidates = []
    for hit in hits:
        payload = hit.payload.copy()
        title = (payload.get("title") or "").lower()
        description = (payload.get("description") or "").lower()
        haystack = f"{title} {description}"

        if not any(t in haystack for t in query_tokens):
            continue

        boost = _keyword_boost(payload, query_tokens)
        final_score = round(min(1.0, hit.score + boost), 4)

        payload["item_id"] = hit.id
        payload["similarity_score"] = final_score
        payload["search_type"] = "keyword_fallback"
        candidates.append((final_score, payload))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in candidates[:limit]]


# ---------------------------------------------------------------------------
# Feed metadata helper
# ---------------------------------------------------------------------------

def _attach_feed_info(articles: List[dict]) -> List[dict]:
    """Joins feed metadata (title, icon, link) into each article dict."""
    feed_hashes = list({a["feed_sha256"] for a in articles if a.get("feed_sha256")})
    if not feed_hashes:
        return articles

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            placeholders = ",".join(["%s"] * len(feed_hashes))
            cursor.execute(
                f"SELECT feed_sha256, feed_title, feed_icon, feed_link "
                f"FROM feeds WHERE feed_sha256 IN ({placeholders})",
                tuple(feed_hashes),
            )
            feeds_info = {row["feed_sha256"]: row for row in cursor.fetchall()}
        finally:
            cursor.close()

    for article in articles:
        info = feeds_info.get(article.get("feed_sha256"))
        if info:
            article["feed_title"] = info["feed_title"]
            article["feed_icon"] = info["feed_icon"]
            article["feed_link"] = info["feed_link"]

    return articles


# ---------------------------------------------------------------------------
# Main search function
# ---------------------------------------------------------------------------

def search_articles_by_text(
    query: str,
    limit: int = 10,
    min_similarity: float = 0.55,
    min_days: Optional[int] = None,   # ADDED: artigos publicados há pelo menos N dias
    max_days: Optional[int] = None,
    feed_filter: Optional[List[str]] = None,
) -> List[dict]:
    """
    Hybrid search over RSS articles.

    Strategy
    --------
    1. Parse quoted phrases (literal) vs free text (semantic).
    2. Embed the free-text portion; use quoted phrases as a Qdrant payload
       filter so they are enforced at the vector-DB level.
    3. Lower the score threshold automatically for short / keyword queries
       (single name, country, ticker) to avoid returning nothing.
    4. Re-rank results with a keyword-overlap boost so token matches
       surface to the top regardless of description presence.
    5. If semantic search returns nothing AND the query has no quoted
       phrases, fall back to a Qdrant scan with no threshold, keeping
       only results that contain at least one query token.

    Parameters
    ----------
    query          : Raw user query, may contain "quoted phrases".
    limit          : Maximum articles to return.
    min_similarity : Base cosine-similarity threshold (dynamically adjusted).
    min_days       : Restrict to articles published at least N days ago
                     (i.e. pub_timestamp <= now - min_days).
                     Useful for "notícias antigas" or recortes como
                     "entre 3 e 7 dias atrás" combinado com max_days=7.
    max_days       : Restrict to articles published within this many days
                     (i.e. pub_timestamp >= now - max_days).
    feed_filter    : Restrict to specific feed SHA-256 hashes.
    """
    query = query.strip()
    if not query:
        return []

    # ── 1. Parse ────────────────────────────────────────────────────────────
    quoted_phrases, semantic_query = parse_query(query)

    # Text to embed: prefer the free-text part; fall back to quoted phrases
    vector_query = semantic_query or " ".join(quoted_phrases)

    # ── 2. Dynamic threshold ─────────────────────────────────────────────
    # Short keyword queries ("France", "Moro", "STF") produce low-magnitude
    # vectors; relax the threshold so results are not silently dropped.
    if _is_short_query(vector_query) and not quoted_phrases:
        effective_threshold = max(0.30, min_similarity - 0.20)
    else:
        effective_threshold = min_similarity

    # ── 3. Embed ─────────────────────────────────────────────────────────
    try:
        vector = embedding_text(vector_query)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Embedding error: {exc}") from exc

    # ── 4. Build Qdrant filter ───────────────────────────────────────────
    must: List[models.Condition] = []

    now_ts = datetime.now(timezone.utc).timestamp()

    # max_days → limite superior: pub_timestamp >= (now - max_days)
    if max_days is not None:
        must.append(
            models.FieldCondition(
                key="pub_timestamp",
                range=models.Range(gte=now_ts - (max_days * 24 * 3600)),
            )
        )

    # min_days → limite inferior: pub_timestamp <= (now - min_days)
    # Garante que artigos mais recentes que N dias sejam excluídos.
    if min_days is not None:
        must.append(
            models.FieldCondition(
                key="pub_timestamp",
                range=models.Range(lte=now_ts - (min_days * 24 * 3600)),
            )
        )

    if feed_filter:
        must.append(
            models.FieldCondition(
                key="feed_sha256",
                match=models.MatchAny(any=feed_filter),
            )
        )

    # Quoted phrases: enforced at DB level (fast) AND re-checked below (safe)
    for phrase in quoted_phrases:
        must.append(
            models.FieldCondition(
                key="title",
                match=models.MatchText(text=phrase),
            )
        )

    qdrant_filter = models.Filter(must=must) if must else None

    # ── 5. Vector search ─────────────────────────────────────────────────
    # Fetch more candidates than needed so re-ranking has material to work with
    client = get_qdrant_client()
    result = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        query_filter=qdrant_filter,
        limit=limit * 4,          # over-fetch for re-ranking
        score_threshold=effective_threshold,
        with_payload=True,
        with_vectors=False,
    )
    hits = result.points

    # ── 6. Re-rank with keyword boost ────────────────────────────────────
    query_tokens = _tokenize(vector_query)
    candidates: List[Tuple[float, dict]] = []

    for hit in hits:
        payload = hit.payload.copy()

        # Hard filter: quoted phrases must literally appear in the title
        if quoted_phrases:
            title_lower = (payload.get("title") or "").lower()
            if not all(p.lower() in title_lower for p in quoted_phrases):
                continue

        boost = _keyword_boost(payload, query_tokens)
        final_score = min(1.0, hit.score + boost)

        payload["item_id"] = hit.id
        payload["similarity_score"] = round(final_score, 4)
        candidates.append((final_score, payload))

    candidates.sort(key=lambda x: x[0], reverse=True)
    articles = [p for _, p in candidates[:limit]]

    # ── 7. Attach feed metadata ──────────────────────────────────────────
    if articles:
        articles = _attach_feed_info(articles)

    # ── 8. Keyword fallback (Qdrant-only, no score threshold) ───────────────
    # Only triggered when semantic search returns nothing AND there are no
    # quoted phrases (a quoted-phrase miss should correctly return empty).
    if not articles and not quoted_phrases:
        articles = _keyword_fallback(
            vector=vector,
            query_tokens=query_tokens,
            limit=limit,
            qdrant_filter=qdrant_filter,
            client=client,
        )
        if articles:
            articles = _attach_feed_info(articles)

    return articles