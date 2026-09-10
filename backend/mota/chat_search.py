"""
mota/chat_search.py — Search orchestration and post-processing pipeline.

Handles the full search lifecycle:
  1. Execute local (Qdrant) and/or online (DuckDuckGo news + web) searches
     — all queries run in parallel via ThreadPoolExecutor
  2. Strip HTML, truncate per-article content
  3. Deduplicate by normalized URL
  4. Apply recency boost and re-sort
  5. Apply total context token budget
  6. Format digests compactly for the LLM (with stable citation ids when a
     SourceRegistry assigner is provided)
"""

from __future__ import annotations

import ast
import json
import logging
import math
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Callable, Optional

from mota.chat_config import (
    CONTENT_CHAR_LIMIT,
    SEARCH_THRESHOLD,
    POSTS_PER_QUERY_LOCAL_ONLINE,
    POSTS_PER_QUERY_MIXED,
    RECENCY_HALF_LIFE_DAYS,
    RECENCY_BOOST_WEIGHT,
    ENABLE_WEB_VERTICAL,
)
from mota.tokens import (
    count_tokens,
    DEFAULT_CONTEXT_TOKEN_BUDGET,
    MIN_TOKENS_PER_ARTICLE,
)
from search.item.search_item import search_articles_by_text
from search.item.search_item_online import search_articles_online

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# TEXT UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def _strip_html(text: str) -> str:
    """Remove tags HTML e normaliza espaços."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", clean).strip()


def _truncate_content(text: str, limit: int = CONTENT_CHAR_LIMIT) -> str:
    """Trunca texto respeitando o limite de caracteres."""
    if not text or len(text) <= limit:
        return text
    truncated = text[:limit]
    logger.info(f"[TRUNCATE] Conteúdo truncado: {len(text)} → {len(truncated)} chars")
    return truncated


def _enrich_with_full_text(article: dict) -> dict:
    """
    Enriquece artigo com leitura profunda do link.
    Extrai texto completo da URL e combina com description existente.
    """
    url = article.get("link", "")
    if not url:
        return article

    logger.info(f"[DEEP READ] Extraindo texto de: {url}")

    try:
        from search.item.search_item_online import extract_text_from_url
        full_text = extract_text_from_url(url)
    except Exception as e:
        logger.error(f"[DEEP READ] Erro ao extrair texto: {e}")
        return article

    if not full_text:
        logger.warning(f"[DEEP READ] Nenhum texto extraído de {url}")
        return article

    existing = _strip_html(article.get("description", ""))

    if existing and existing[:80].lower() in full_text.lower():
        combined = full_text
    else:
        combined = f"{existing}\n\n{full_text}" if existing else full_text

    article["description"] = _truncate_content(combined)
    article["deep_read"] = True

    logger.info(f"[DEEP READ] ✓ Texto extraído: {len(article['description'])} chars")
    return article


def _format_article_digest(idx: int, article: dict) -> str:
    """
    Formato compacto: título, data, fonte, link + descrição curta.
    ~80-100 tokens/artigo vs ~200+ do formato completo.
    """
    title = article.get("title", "Sem título")
    pub_date = (article.get("pub_date") or "")[:10]
    feed_title = article.get("feed_title", "")
    link = article.get("link", "")
    description = _strip_html(article.get("description", ""))[:300]
    header = f"[{idx}] {pub_date} — {title} ({feed_title})"
    return f"{header}\n{link}\n{description}" if description else f"{header}\n{link}"


def _format_article_for_llm(idx: int, article: dict) -> str:
    """
    Formata artigo para envio ao LLM (usado no modo artigos diretos).
    """
    title = article.get("title", "Sem título")
    description = _strip_html(article.get("description", ""))
    pub_date = (article.get("pub_date") or "")[:10]
    feed_title = article.get("feed_title", "")
    link = article.get("link", "")
    deep = " [leitura profunda]" if article.get("deep_read") else ""

    header = f"[{idx}]{deep} {pub_date} — {title} ({feed_title})"

    return f"{header}\n{link}\n{description}"


# ══════════════════════════════════════════════════════════════════════════════
# RECENCY BOOST
# ══════════════════════════════════════════════════════════════════════════════

def _get_article_age_days(article: dict, now: datetime) -> Optional[float]:
    """
    Calcula a idade do artigo em dias a partir de pub_date.

    Returns:
    Idade em dias (float), ou None se não for possível determinar.
    """
    pub_date = article.get("pub_date")
    if not pub_date:
        return None

    try:
        if isinstance(pub_date, datetime):
            article_dt = pub_date
            if article_dt.tzinfo is None:
                article_dt = article_dt.replace(tzinfo=timezone.utc)
        elif isinstance(pub_date, str):
            pub_str = pub_date.strip()[:19]
            article_dt = datetime.fromisoformat(pub_str)
            if article_dt.tzinfo is None:
                article_dt = article_dt.replace(tzinfo=timezone.utc)
        else:
            return None

        delta = now - article_dt
        return max(0.0, delta.total_seconds() / 86400.0)
    except (ValueError, TypeError, OverflowError):
        return None


def _apply_recency_boost(
    articles: list[dict],
    half_life: float = RECENCY_HALF_LIFE_DAYS,
    weight: float = RECENCY_BOOST_WEIGHT,
) -> list[dict]:
    """
    Aplica boost de recência aos scores de similaridade dos artigos.

    Fórmula: boosted_score = similarity + weight × exp(−age_days / half_life)
    """
    if not articles:
        return articles

    now = datetime.now(timezone.utc)

    for art in articles:
        raw_score = art.get("similarity_score")
        if raw_score is None:
            raw_score = 0.5

        art["similarity_score_raw"] = raw_score

        age_days = _get_article_age_days(art, now)

        if age_days is not None and age_days >= 0:
            recency_factor = math.exp(-age_days / half_life)
            boost = weight * recency_factor
            art["similarity_score"] = raw_score + boost
            art["recency_boost"] = round(boost, 4)
            art["_age_days"] = round(age_days, 1)
        else:
            art["similarity_score"] = raw_score
            art["recency_boost"] = 0.0
            art["_age_days"] = None

    articles.sort(key=lambda a: a.get("similarity_score", 0), reverse=True)

    return articles


# ══════════════════════════════════════════════════════════════════════════════
# DEDUPLICAÇÃO DE ARTIGOS
# ══════════════════════════════════════════════════════════════════════════════

_CHAT_PUB_AFFINITY_WEIGHT = 0.08


def _apply_publisher_boost(
    articles: list[dict],
    publisher_affinity: Optional[dict],
) -> list[dict]:
    """
    Boost leve (+−0.08) para resultados LOCAIS de feeds cujo engajamento
    o usuário aprendeu (likes − dislikes). Reordena após o recency boost.
    Só afeta o ranking — nunca é explicado ao modelo.
    """
    likes_map = publisher_affinity.get("likes") or {}
    dislikes_map = publisher_affinity.get("dislikes") or {}
    if not likes_map and not dislikes_map:
        return articles

    boosted = 0
    for art in articles:
        feed_hash = art.get("feed_sha256")
        if not feed_hash or art.get("search_type") != "local":
            continue
        likes = float(likes_map.get(feed_hash, 0))
        dislikes = float(dislikes_map.get(feed_hash, 0))
        if likes == dislikes:
            continue
        boost = _CHAT_PUB_AFFINITY_WEIGHT * math.tanh((likes - dislikes) / 3.0)
        if boost == 0:
            continue
        art["similarity_score_raw"] = art.get("similarity_score_raw", art.get("similarity_score", 0))
        art["similarity_score"] = art["similarity_score_raw"] + boost
        art["publisher_boost"] = round(boost, 4)
        boosted += 1

    articles.sort(key=lambda a: a.get("similarity_score", 0), reverse=True)
    if boosted:
        logger.info(f"[PUB_AFFINITY] {boosted} artigos locais reordenados por engajamento")

    return articles


def _normalize_url(url: str) -> str:
    """Normalizes URL for duplicate comparison."""
    if not url:
        return ""
    url = url.lower().strip()
    url = re.sub(r'^https?://(www\.)?', '', url)
    url = re.sub(r'[?#].*$', '', url)
    url = re.sub(r'/+$', '', url)
    return url


def _deduplicate_articles(articles: list[dict]) -> list[dict]:
    """
    Remove artigos duplicados por URL normalizada (e título idêntico).
    """
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    unique: list[dict] = []

    for art in articles:
        url = _normalize_url(art.get("link", ""))
        title_key = re.sub(r"\s+", " ", art.get("title", "").strip().lower())[:80]

        if url and url in seen_urls:
            continue
        if title_key and title_key in seen_titles:
            continue

        if url:
            seen_urls.add(url)
        if title_key:
            seen_titles.add(title_key)
        unique.append(art)

    return unique


# ══════════════════════════════════════════════════════════════════════════════
# ORÇAMENTO DE CONTEXTO
# ══════════════════════════════════════════════════════════════════════════════

def _apply_context_budget(
    articles: list[dict],
    budget: int = DEFAULT_CONTEXT_TOKEN_BUDGET,
    model: str | None = None,
) -> list[dict]:
    """
    Aplica orçamento total de contexto (em tokens), truncando artigos menos relevantes.
    Usa litellm.token_counter (provider-aware), com fallback heurístico (chars / 4).
    """
    if not articles:
        return articles

    token_costs = [count_tokens(a.get("description", ""), model) for a in articles]
    total = sum(token_costs)

    if total <= budget:
        logger.info(f"[BUDGET] Conteúdo total {total} tokens ≤ orçamento {budget}")
        return articles

    logger.info(f"[BUDGET] Conteúdo total {total} tokens > orçamento {budget} — truncando...")

    remaining = budget
    min_per = MIN_TOKENS_PER_ARTICLE

    for i, art in enumerate(articles):
        desc = art.get("description", "")
        desc_chars = len(desc)
        cost = token_costs[i]

        if cost <= remaining:
            remaining -= cost
        elif remaining > min_per:
            keep_chars = max(min_per * 4, int(desc_chars * remaining / max(cost, 1)))
            art["description"] = desc[:keep_chars].rstrip() + "\n[...]"
            remaining = 0
        else:
            if desc_chars > min_per * 4:
                art["description"] = desc[: min_per * 4].rstrip() + "\n[...]"

    final_total = sum(count_tokens(a.get("description", ""), model) for a in articles)
    logger.info(f"[BUDGET] Resultado: {total} → {final_total} tokens")

    return articles


# ══════════════════════════════════════════════════════════════════════════════
# BUSCA LOCAL
# ══════════════════════════════════════════════════════════════════════════════

def _call_local(
    query: str,
    limit: int,
    min_days: Optional[int],
    max_days: Optional[int],
    feed_filter: Optional[list[str]] = None,
) -> list[dict]:
    """Executes local search in the feed database (Qdrant semantic)."""
    logger.info(
        f"[LOCAL] search_articles_by_text({query!r}, limit={limit}, "
        f"min_days={min_days}, max_days={max_days}, "
        f"feed_filter={len(feed_filter) if feed_filter else 'none'})"
    )

    # Empty feed_filter means the user's "mine" scope matched no subscriptions
    if feed_filter is not None and len(feed_filter) == 0:
        return []

    try:
        results = search_articles_by_text(
            query=query,
            limit=limit,
            min_similarity=SEARCH_THRESHOLD,
            min_days=min_days,
            max_days=max_days,
            feed_filter=feed_filter,
        )
        logger.info(f"[LOCAL] ✓ {len(results)} artigos retornados")
        return results
    except Exception as e:
        logger.error(f"[LOCAL] ✗ Erro em search_articles_by_text: {e}", exc_info=True)
        return []


# ══════════════════════════════════════════════════════════════════════════════
# VALIDAÇÃO DE BUSCAS
# ══════════════════════════════════════════════════════════════════════════════

def _normalize_searches(searches: list) -> list[dict]:
    """Normalizes search list to ensure consistent format."""
    safe: list[dict] = []

    for item in searches:
        if isinstance(item, dict):
            safe.append(item)
        elif isinstance(item, str):
            try:
                parsed = json.loads(item)
                if isinstance(parsed, dict):
                    safe.append(parsed)
                else:
                    safe.append({"query": item})
            except json.JSONDecodeError:
                try:
                    parsed = ast.literal_eval(item)
                    if isinstance(parsed, dict):
                        safe.append(parsed)
                    else:
                        safe.append({"query": item})
                except (ValueError, SyntaxError):
                    safe.append({"query": item})
        else:
            logger.warning(f"[NORMALIZE] Search item tipo inesperado ({type(item)})")

    return safe


# ══════════════════════════════════════════════════════════════════════════════
# ORQUESTRAÇÃO DE BUSCAS
# ══════════════════════════════════════════════════════════════════════════════

def _get_posts_distribution(num_queries: int, source_mode: str) -> tuple[int, int]:
    """Calculates local/online post distribution per query."""
    if source_mode == "mixed":
        total = POSTS_PER_QUERY_MIXED.get(num_queries, 4)
        local_per = total // 2
        online_per = total - local_per
    elif source_mode == "online":
        total = POSTS_PER_QUERY_LOCAL_ONLINE.get(num_queries, 2)
        local_per, online_per = 0, total
    else:  # local
        total = POSTS_PER_QUERY_LOCAL_ONLINE.get(num_queries, 2)
        local_per, online_per = total, 0

    return local_per, online_per


def _execute_one_search(
    search: dict,
    local_per: int,
    online_per: int,
    feed_filter: Optional[list[str]],
) -> list[dict]:
    """Runs a single sub-query (local +/or online) and returns cleaned articles."""
    query = search.get("query", "")
    min_days = search.get("min_days")
    max_days = search.get("max_days")
    vertical = search.get("vertical", "news")

    collected: list[dict] = []

    if local_per > 0:
        for art in _call_local(query, local_per, min_days, max_days, feed_filter=feed_filter):
            art["search_type"] = art.get("search_type", "local")
            if art.get("description"):
                art["description"] = _truncate_content(_strip_html(art["description"]))
            collected.append(art)

    if online_per > 0:
        if not ENABLE_WEB_VERTICAL and vertical == "web":
            vertical = "news"  # web vertical disabled via env
        online_count = 0
        try:
            results = search_articles_online(
                query,
                limit=online_per,
                max_days=max_days,
                min_days=min_days,
                fetch_full_text=False,
                vertical=vertical,
            )
            for art in results:
                if art.get("description"):
                    art["description"] = _truncate_content(_strip_html(art["description"]))
            online_count = len(results)
            collected.extend(results)
        except Exception as e:
            logger.error(f" [ONLINE] ✗ Erro: {e}")
            online_count = 0

        # Auto web-vertical retry: news returned nothing → fall back to
        # general web once (recency weighting in run_searches handles dates).
        if (
            online_count == 0
            and vertical == "news"
            and ENABLE_WEB_VERTICAL
        ):
            try:
                results = search_articles_online(
                    query,
                    limit=online_per,
                    max_days=max_days,
                    min_days=min_days,
                    fetch_full_text=False,
                    vertical="web",
                )
                for art in results:
                    if art.get("description"):
                        art["description"] = _truncate_content(_strip_html(art["description"]))
                if results:
                    logger.info(" [ONLINE] ↻ news vazio → vertical web fallback: %d artigos", len(results))
                collected.extend(results)
            except Exception as e:
                logger.error(f" [ONLINE] ✗ Erro no fallback web: {e}")

    return collected


def run_searches(
    searches: list[dict],
    source_mode: str = "local",
    feed_filter: Optional[list[str]] = None,
    id_assigner: Callable[[dict], int] | None = None,
    token_budget: int = DEFAULT_CONTEXT_TOKEN_BUDGET,
    publisher_affinity: Optional[dict] = None,
) -> tuple[str, list[dict]]:
    """
    Executa múltiplas buscas (em paralelo) e consolida os resultados.

    Args:
        searches: lista de {query, vertical?, min_days?, max_days?}
        source_mode: "local" | "online" | "mixed"
        feed_filter: feed_sha256 subscriptions (None = escopo global)
        id_assigner: callable(article) → citation id usado no digest; quando
                     ausente usa 1..N relativo.
        token_budget: orçamento total de tokens para descrições.
        publisher_affinity: {'likes': {feed: n}, 'dislikes': {feed: n}} do
                     perfil do usuário; aplica boost leve a resultados locais
                     de feeds com engajamento positivo/negativo.

    Returns:
        (texto formatado para o LLM, lista de artigos únicos)
    """
    searches = _normalize_searches(searches)
    num_queries = len(searches)

    logger.info(f"[SEARCH] Queries: {num_queries} | Modo: {source_mode} | "
                f"feed_filter: {len(feed_filter) if feed_filter else 'none (global)'}")

    all_articles: list[dict] = []
    local_per, online_per = _get_posts_distribution(num_queries, source_mode)

    logger.info(f"[SEARCH] Distribuição por query → Local: {local_per} Online: {online_per}")

    # ── Fase 1: coleta em paralelo ────────────────────────────────────────────
    if num_queries == 1:
        results_map = [_execute_one_search(searches[0], local_per, online_per, feed_filter)]
    else:
        with ThreadPoolExecutor(max_workers=min(6, num_queries * 2)) as pool:
            futures = [
                pool.submit(_execute_one_search, s, local_per, online_per, feed_filter)
                for s in searches
            ]
            results_map = [f.result() for f in futures]

    for i, (search, arts) in enumerate(zip(searches, results_map), 1):
        logger.info(f"[SEARCH {i}/{num_queries}] {search.get('query', '')!r} → {len(arts)} artigos")
        all_articles.extend(arts)

    # ── Fase 2: pós-processamento ─────────────────────────────────────────────
    all_articles = _deduplicate_articles(all_articles)
    all_articles = _apply_recency_boost(all_articles)
    if publisher_affinity:
        all_articles = _apply_publisher_boost(all_articles, publisher_affinity)
    all_articles = _apply_context_budget(all_articles, budget=token_budget)

    logger.info(f"[SEARCH] ✓ TOTAL: {len(all_articles)} artigos (após dedup + boost)")
    for art in all_articles:
        art.pop("_age_days", None)

    if not all_articles:
        return "No articles found for the searched topics.", []

    # ── Fase 3: digest compacto, com ids de citação contínuos ─────────────────
    if id_assigner is not None:
        intro = ("A seguir estão os artigos encontrados, ordenados por relevância e recência. "
                 "Os números entre colchetes são a fonte citável:\n")
        body = "\n\n".join(_format_article_digest(id_assigner(a), a) for a in all_articles)
    else:
        intro = ("A seguir estão os artigos encontrados, ordenados por relevância e recência. "
                 "Sintetize as informações em uma resposta clara:\n")
        body = "\n\n".join(_format_article_digest(i, a) for i, a in enumerate(all_articles, 1))

    return f"{intro}{body}", all_articles
