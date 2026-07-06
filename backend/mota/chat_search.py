"""
mota/chat_search.py — Search orchestration and post-processing pipeline.

Handles the full search lifecycle:
  1. Execute local (Qdrant) and/or online (DuckDuckGo) searches
  2. Strip HTML, truncate per-article content
  3. Deduplicate by normalized URL
  4. Apply recency boost and re-sort
  5. Selective deep reading (top N local articles)
  6. Apply total context budget
  7. Format articles compactly for the LLM
"""

from __future__ import annotations

import ast
import json
import logging
import math
import re
from datetime import datetime, timezone
from typing import Optional

from mota.chat_config import (
    CONTENT_CHAR_LIMIT,
    TOTAL_CONTEXT_CHAR_LIMIT,
    SEARCH_THRESHOLD,
    MAX_DEEP_READ_ARTICLES,
    RECENCY_HALF_LIFE_DAYS,
    RECENCY_BOOST_WEIGHT,
    POSTS_PER_QUERY_LOCAL_ONLINE,
    POSTS_PER_QUERY_MIXED,
)
from mota.tokens import (
    count_tokens,
    DEFAULT_CONTEXT_TOKEN_BUDGET,
    MIN_TOKENS_PER_ARTICLE,
)
from search.item.search_item import search_articles_by_text
from search.item.search_item_online import search_articles_online, extract_text_from_url

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


def _format_article_for_llm(idx: int, article: dict) -> str:
    """
    Formata artigo para envio ao LLM (formato compacto para economia de tokens).
    """
    title = article.get("title", "Sem título")
    description = _strip_html(article.get("description", ""))
    pub_date = (article.get("pub_date") or "")[:10]
    feed_title = article.get("feed_title", "")
    link = article.get("link", "")
    deep = " [leitura profunda]" if article.get("deep_read") else ""

    header = f"[{idx}]{deep} {pub_date} — {title} ({feed_title})"

    return f"{header}\n{link}\n{description}"


def _format_article_digest(idx: int, article: dict) -> str:
    """
    Formato compacto: título, data, fonte, link + descrição curta.
    ~80-100 tokens/artigo vs ~200+ do formato completo.
    Inclui descrição suficiente para o modelo responder sem deep reading.
    """
    title = article.get("title", "Sem título")
    pub_date = (article.get("pub_date") or "")[:10]
    feed_title = article.get("feed_title", "")
    link = article.get("link", "")
    description = _strip_html(article.get("description", ""))[:300]
    header = f"[{idx}] {pub_date} — {title} ({feed_title})"
    return f"{header}\n{link}\n{description}" if description else f"{header}\n{link}"


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

    Artigos mais recentes recebem um aumento no score, permitindo que
    conteúdo atual seja priorizado sobre conteúdo antigo mesmo com
    similaridade semântica ligeiramente menor.

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

    logger.info(f"[RECENCY] Ranking após boost (half_life={half_life}, weight={weight}):")
    for i, art in enumerate(articles[:10], 1):
        raw = art.get("similarity_score_raw", 0)
        boosted = art.get("similarity_score", 0)
        boost = art.get("recency_boost", 0)
        age = art.get("_age_days", "?")
        title = art.get("title", "")[:60]
        logger.info(
            f" {i}. score {raw:.3f}→{boosted:.3f} (+{boost:.3f}) "
            f"age={age}d | {title}"
        )

    return articles


# ══════════════════════════════════════════════════════════════════════════════
# DEDUPLICAÇÃO DE ARTIGOS
# ══════════════════════════════════════════════════════════════════════════════

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
    Remove artigos duplicados por URL normalizada.
    Mantém a primeira ocorrência (que deve ter o maior score após ordenação).
    """
    seen: set[str] = set()
    unique: list[dict] = []
    dupes_removed = 0

    for art in articles:
        url = _normalize_url(art.get("link", ""))

        if url and url in seen:
            dupes_removed += 1
            continue

        if url:
            seen.add(url)
        unique.append(art)

    if dupes_removed:
        logger.info(f"[DEDUP] {dupes_removed} duplicata(s) removida(s) → {len(unique)} únicos")

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

    Artigos já estão ordenados por score boostado (melhores primeiro).
    Os primeiros recebem conteúdo completo; os últimos podem ser truncados
    se o orçamento for excedido.

    Usa litellm.token_counter (provider-aware) quando possível, com fallback
    heurístico (chars / 4) se a tokenização falhar.
    """
    if not articles:
        return articles

    # Compute token cost per article's description
    token_costs = []
    for art in articles:
        desc = art.get("description", "")
        token_costs.append(count_tokens(desc, model))

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
            # Truncate proportionally to fit remaining token budget
            keep_chars = max(min_per * 4, int(desc_chars * remaining / max(cost, 1)))
            art["description"] = desc[:keep_chars].rstrip() + "\n[...]"
            remaining = 0
        else:
            # Not enough budget left — keep the minimum snippet
            if desc_chars > min_per * 4:
                art["description"] = desc[: min_per * 4].rstrip() + "\n[...]"

    final_total = sum(count_tokens(a.get("description", ""), model) for a in articles)
    logger.info(f"[BUDGET] Resultado: {total} → {final_total} tokens")

    return articles


# ══════════════════════════════════════════════════════════════════════════════
# DEEP READING SELETIVO
# ══════════════════════════════════════════════════════════════════════════════

def _selective_deep_read(
    articles: list[dict],
    max_articles: int = MAX_DEEP_READ_ARTICLES,
) -> list[dict]:
    """
    Faz leitura profunda apenas dos top N artigos locais por score.

    Artigos online já possuem texto completo (busca online faz fetch).
    Limitar deep reading a N artigos economiza bandwidth e tempo
    em servidores caseiros.

    Os artigos já devem estar ordenados por score boostado.
    """
    if not articles:
        return articles

    deep_count = 0
    local_count = 0

    for art in articles:
        if deep_count >= max_articles:
            break

        if art.get("search_type") == "online" or art.get("deep_read"):
            continue

        local_count += 1
        _enrich_with_full_text(art)
        deep_count += 1

    logger.info(
        f"[DEEP SELECTIVE] {deep_count} artigos lidos "
        f"(de {local_count} locais elegíveis, limite={max_articles})"
    )

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
    """Executes local search in the user's feed database."""
    logger.info(
        f"[LOCAL] search_articles_by_text({query!r}, limit={limit}, "
        f"min_days={min_days}, max_days={max_days}, "
        f"feed_filter={len(feed_filter) if feed_filter else 'none'})"
    )

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
            logger.warning(f"[NORMALIZE] Search item era string: {item[:100]}")
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


def run_searches(
    searches: list[dict],
    source_mode: str = "local",
    deep_reading: bool = False,
    feed_filter: Optional[list[str]] = None,
) -> tuple[str, list[dict]]:
    """
    Executa múltiplas buscas e consolida resultados.

    Pipeline pós-busca:
    1. Limpa HTML e trunca por artigo
    2. Deduplica por URL
    3. Aplica recency boost e re-ordena
    4. Deep reading seletivo (top N)
    5. Aplica orçamento de contexto
    6. Formata para o LLM

    Args:
        feed_filter: lista de feed_sha256 para restringir a busca local
                     (subscriptions do usuário). None = sem restrição (escopo global).
    """
    searches = _normalize_searches(searches)
    num_queries = len(searches)

    local_per, online_per = _get_posts_distribution(num_queries, source_mode)

    logger.info(f"\n{'='*70}")
    logger.info(f"[SEARCH] Iniciando buscas")
    logger.info(f"[SEARCH] Queries: {num_queries} | Modo: {source_mode} | Deep: {deep_reading}")
    logger.info(f"[SEARCH] feed_filter: {len(feed_filter) if feed_filter else 'none (global)'}")
    logger.info(f"[SEARCH] Distribuição por query → Local: {local_per} Online: {online_per}")
    logger.info(f"{'='*70}")

    all_articles: list[dict] = []

    # ── Fase 1: Coleta de artigos ──────────────────────────────────────────
    for i, search in enumerate(searches, 1):
        query = search.get("query", "")
        min_days = search.get("min_days")
        max_days = search.get("max_days")

        logger.info(f"\n[SEARCH {i}/{num_queries}] '{query}' (min={min_days}, max={max_days})")

        # Busca local
        if local_per > 0:
            local_results = _call_local(
                query, local_per, min_days, max_days, feed_filter=feed_filter
            )
            local_cut = local_results[:local_per]

            for art in local_cut:
                art["search_type"] = art.get("search_type", "local")
                if art.get("description"):
                    art["description"] = _truncate_content(_strip_html(art["description"]))

            all_articles.extend(local_cut)
            logger.info(f" [LOCAL] {len(local_cut)} artigos")

        # Busca online
        if online_per > 0:
            try:
                online_results = search_articles_online(
                    query,
                    limit=online_per,
                    max_days=max_days,
                    min_days=min_days,
                    fetch_full_text=True,
                )
                online_cut = online_results[:online_per]

                for art in online_cut:
                    if art.get("description"):
                        art["description"] = _truncate_content(_strip_html(art["description"]))

                all_articles.extend(online_cut)
                logger.info(f" [ONLINE] {len(online_cut)} artigos")
            except Exception as e:
                logger.error(f" [ONLINE] ✗ Erro: {e}")

    # ── Phase 2: Post-processing pipeline ──────────────────────────────────

    # 2a. Deduplicação por URL
    all_articles = _deduplicate_articles(all_articles)

    # 2b. Recency boost — prioriza artigos recentes
    all_articles = _apply_recency_boost(all_articles)

    # 2c. Deep reading is now on-demand via the read_article tool.
    #     The blind top-N prefetch is skipped to save tokens and bandwidth;
    #     the model can request full text for specific articles it wants to cite.
    #     (Deep reading for direct articles in _handle_direct_articles is unaffected.)

    # 2d. Context budget — truncates less relevant articles
    all_articles = _apply_context_budget(all_articles)

    # ── Fase 3: Log consolidado ────────────────────────────────────────────
    logger.info(f"\n{'='*70}")
    logger.info(f"[SEARCH] ✓ TOTAL: {len(all_articles)} artigos (após dedup + boost)")
    logger.info(f"{'='*70}")

    for idx, art in enumerate(all_articles, 1):
        desc = _strip_html(art.get("description", ""))
        deep_tag = " [deep]" if art.get("deep_read") else ""
        raw_score = art.get("similarity_score_raw", 0)
        boosted_score = art.get("similarity_score", 0)
        boost = art.get("recency_boost", 0)
        age = art.get("_age_days", "?")
        source = art.get("search_type", "")

        logger.info(
            f" [{idx}]{deep_tag} {source} | raw={raw_score:.3f} "
            f"boosted={boosted_score:.3f} (+{boost:.3f}) age={age}d | "
            f"{art.get('feed_title', '')} | {art.get('title', '')}"
        )
        logger.info(f" ({len(desc)} chars): {desc[:120]}{'...' if len(desc) > 120 else ''}")

    logger.info(f"{'='*70}\n")

    if not all_articles:
        return "No articles found for the searched topics.", []

    # ── Phase 4: Compact digest for the LLM ────────────────────────────────
    # Include title + short description so the model can answer without
    # needing to deep-read every article.
    blocks = [
        "A seguir estão os artigos encontrados, ordenados por relevância e recência. "
        "Sintetize as informações em uma resposta clara:\n"
    ]

    for idx, article in enumerate(all_articles, 1):
        blocks.append(_format_article_digest(idx, article))

    return "\n\n".join(blocks), all_articles
