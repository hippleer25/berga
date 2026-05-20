"""
search_item_online.py
─────────────────────
Busca artigos de notícias online usando DuckDuckGo e extrai o texto completo
das páginas. Retorna dicts no mesmo formato que a API local de /search, para
que o chat.py os processe de forma uniforme.

Dependências:
    pip install ddgs requests readability-lxml
    (readability-lxml já deve estar no requirements.txt do projeto)
"""

import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from readability import Document
from ddgs import DDGS
from i18n.locale_map import ddg_region, accept_language_header

logger = logging.getLogger(__name__)


def _parse_date(date_str: str) -> datetime | None:
    """Attempts to parse article date in multiple formats."""
    if not date_str:
        return None

    # ISO 8601 (most common DDGS format)
    for fmt in [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d",
    ]:
        try:
            dt = datetime.strptime(date_str.strip()[:26], fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, IndexError):
            continue

    return None


# ── Configurações ────────────────────────────────────────────────────────────

REQUEST_TIMEOUT = 8          # seconds per page fetch
MAX_TEXT_CHARS  = 4000       # extracted text limit (to avoid overloading the AI)

# Domains that are not primary news sources
BLACKLIST = {
    "wikipedia.org", "wikimedia.org",
    "news.google.com", "google.com",
    "reddit.com", "facebook.com",
    "twitter.com", "x.com",
    "linkedin.com", "youtube.com",
    "amazon.com", "instagram.com",
    "tiktok.com", "pinterest.com",
}

# Headers to simulate a real browser and avoid blocks
_BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def _headers() -> dict:
    h = dict(_BASE_HEADERS)
    h["Accept-Language"] = accept_language_header()
    return h


# ── Helpers ──────────────────────────────────────────────────────────────────

def _domain(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "").lower()


def _is_blacklisted(url: str) -> bool:
    d = _domain(url)
    return any(d == b or d.endswith("." + b) for b in BLACKLIST)


def _score_result(r: dict) -> float:
    """
    Pontua um resultado do DDGS para priorizar fontes jornalísticas.
    Retorna -1.0 para domínios na blacklist.
    """
    url = r.get("url", r.get("href", ""))
    if _is_blacklisted(url):
        return -1.0

    score = 0.0
    parsed = urlparse(url)

    # HTTPS preferível
    if parsed.scheme == "https":
        score += 2.0

    # Penaliza URLs muito profundas (agregadores de feeds)
    depth = len([p for p in parsed.path.split("/") if p])
    if depth <= 3:
        score += 1.0
    elif depth >= 6:
        score -= 1.0

    # Penalizes excessive query parameters (tracking links)
    if len(parsed.query) > 80:
        score -= 0.5

    return score


# ── Extração de texto ────────────────────────────────────────────────────────

def extract_text_from_url(url: str) -> str:
    """
    Extrai o texto principal de uma página web usando readability-lxml
    (o mesmo algoritmo do Firefox Reader Mode, já presente no projeto em post/load.py).

    readability retorna HTML limpo — fazemos strip das tags para entregar
    texto puro à IA, sem overhead de dependência nova.
    Retorna string vazia em caso de erro.
    """
    try:
        response = requests.get(url, headers=_headers(), timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        # readability extracts the main article block as HTML
        doc = Document(response.text)
        content_html = doc.summary()

        if not content_html:
            return ""

        # Strip HTML tags — AI needs plain text, not markup
        clean = re.sub(r"<script[^>]*>.*?</script>", " ", content_html, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"<style[^>]*>.*?</style>",  " ", clean,        flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"<[^>]+>", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()

        if len(clean) < 100:
            logger.debug(f"readability retornou conteúdo muito curto para {url}")
            return ""

        return clean[:MAX_TEXT_CHARS]

    except requests.RequestException as e:
        logger.warning(f"Falha ao buscar {url}: {e}")
        return ""
    except Exception as e:
        logger.warning(f"Falha ao extrair texto de {url}: {e}")
        return ""


# ── Busca principal ──────────────────────────────────────────────────────────

def search_articles_online(
    query: str,
    limit: int = 6,
    max_days: int | None = None,
    min_days: int | None = None,
    fetch_full_text: bool = False,
) -> list[dict]:
    """
    Busca artigos de notícias no DuckDuckGo e retorna uma lista de dicts
    no mesmo formato da API local de /search.

    Parâmetros
    ----------
    query          : Termos de busca em linguagem natural.
    limit          : Quantidade máxima de artigos a retornar.
    max_days       : Restringe a artigos dos últimos N dias.
                     Mapeia para timelimit do DDGS: 1→'d', 7→'w', 30→'m', else None.
    min_days       : Não suportado nativamente pelo DDGS; usado apenas como filtro
                     de pós-processamento quando combinado com max_days.
    fetch_full_text: Se True, faz fetch de cada URL e extrai o texto completo.
                     Use com moderação — adiciona latência.

    Retorna
    -------
    Lista de dicts com chaves: title, description, link, pub_date,
    feed_title, feed_icon, similarity_score, search_type, author.
    """
    query = query.strip()
    if not query:
        return []

    # Maps max_days to DDGS timelimit
    timelimit: str | None = None
    if max_days is not None:
        if max_days <= 1:
            timelimit = "d"
        elif max_days <= 7:
            timelimit = "w"
        elif max_days <= 30:
            timelimit = "m"
        # > 30 days: DDGS doesn't support, no time filter

    logger.info("[ONLINE] query=%r timelimit=%s limit=%d fetch_full=%s", query, timelimit, limit, fetch_full_text)

    try:
        raw_results = list(DDGS().news(
            query,
            region=ddg_region(),
            safesearch="off",
            timelimit=timelimit,
            max_results=limit * 3,
        ))
    except Exception as e:
        logger.error(f"[ONLINE] Falha na busca DDGS: {e}")
        return []

    logger.info("[ONLINE] %d raw results from DDGS", len(raw_results))

    # Pontua, filtra blacklist e ordena
    scored: list[tuple[float, dict]] = []
    for r in raw_results:
        url   = r.get("url", r.get("href", ""))
        score = _score_result({"url": url})
        if score < 0:
            continue
        scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    candidates = [r for _, r in scored[:limit]]

    logger.info("[ONLINE] %d articles after blacklist filter", len(candidates))

    # Filter by min_days in post-processing (when DDGS doesn't filter)
    if min_days is not None:
        now_ts = datetime.now(timezone.utc).timestamp()
        cutoff = now_ts - (min_days * 24 * 3600)
        filtered = []
        for r in candidates:
            pub_dt = _parse_date(r.get("date", ""))
            if pub_dt is not None:
                if pub_dt.timestamp() <= cutoff:
                    filtered.append(r)
            else:
                filtered.append(r)   # data desconhecida: mantém
        candidates = filtered

    # Converts to standard application format
    articles: list[dict] = []
    for idx, r in enumerate(candidates):
        url       = r.get("url", r.get("href", ""))
        title     = r.get("title", "No title")
        snippet   = r.get("body", r.get("excerpt", ""))
        source    = r.get("source", _domain(url))
        pub_raw   = r.get("date", "")
        pub_dt    = _parse_date(pub_raw)

        # Full text (optional — fetch on demand)
        full_text = ""
        if fetch_full_text and url:
            logger.debug("[ONLINE] Extracting text from %s", url)
            full_text = extract_text_from_url(url)

        description = full_text if full_text else snippet

        # Artificial descending score (DDGS doesn't return similarity)
        similarity = round(max(0.50, 0.95 - idx * 0.05), 4)

        articles.append({
            "title":            title,
            "description":      description,
            "link":             url,
            "pub_date":         pub_raw,
            "pub_timestamp":    int(pub_dt.timestamp()) if pub_dt else None,
            "author":           source,
            "feed_title":       source,
            "feed_icon":        f"https://www.google.com/s2/favicons?domain={url}&sz=128",
            "feed_link":        f"https://{_domain(url)}",
            "similarity_score": similarity,
            "search_type":      "online",
            "url_hash":         None,
            "item_id":          None,
        })

    logger.info("[ONLINE] %d articles returned", len(articles))
    return articles