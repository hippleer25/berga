"""
chat.py
───────
Handler principal do chat do Mota IA.

Fluxo de execução:
1. Artigos diretos do feed  → extração profunda + síntese
2. Mensagem simples          → resposta direta (sem busca)
3. Mensagem que requer info  → tool calling + FALLBACK de busca

O FALLBACK garante que toda pergunta não-trivial dispare busca nas bases,
mesmo quando o LLM não chama a ferramenta.

Melhorias v2:
- Recency boost: artigos recentes recebem boost exponencial no score
- Detecção de recência implícita: perguntas sobre atualidades
  recebem max_days padrão automaticamente
- Deduplicação de artigos por URL normalizada
- Orçamento de contexto dinâmico (prioriza artigos mais relevantes)
- Formatação compacta para economia de tokens na API
- Deep reading seletivo (apenas top N artigos por score)
"""

import os
os.environ.setdefault('LITELLM_LOG', 'WARNING')

import ast
import json
import logging
import math
import re
from datetime import datetime, timezone
from typing import Iterator, Optional

from mota.ai_lib import call_llm_with_tools, stream_llm_response
from search.item.search_item import search_articles_by_text
from search.item.search_item_online import search_articles_online, extract_text_from_url

try:
    from json_repair import repair_json
    HAS_JSON_REPAIR = True
except ImportError:
    HAS_JSON_REPAIR = False

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES
# ══════════════════════════════════════════════════════════════════════════════

# Limite de caracteres por artigo (description + leitura profunda)
CONTENT_CHAR_LIMIT = 6_000

# Orçamento total de conteúdo para o LLM (chars em todas as descriptions)
TOTAL_CONTEXT_CHAR_LIMIT = 40_000

# Threshold mínimo de similaridade para buscas locais
SEARCH_THRESHOLD = 0.6

# Deep reading seletivo — apenas os N melhores artigos
MAX_DEEP_READ_ARTICLES = 3

# ── Recency Boost ────────────────────────────────────────────────────────────
# Fórmula: boosted_score = similarity + WEIGHT × exp(−age / HALF_LIFE)
#
# Exemplos com HALF_LIFE=7, WEIGHT=0.4:
#   0 dias : boost = 0.400  →  score 0.65 vira 1.05
#   7 dias : boost = 0.200  →  score 0.65 vira 0.85
#  14 dias : boost = 0.100  →  score 0.65 vira 0.75
#  30 dias : boost = 0.024  →  score 0.65 vira 0.674
#  90 dias : boost = 0.001  →  praticamente nulo
RECENCY_HALF_LIFE_DAYS = 7.0
RECENCY_BOOST_WEIGHT = 0.4

# Quando a pergunta implica atualidades mas não menciona data explicitamente,
# aplicar max_days padrão
IMPLICIT_RECENCY_MAX_DAYS = 30

# Distribuição de posts por query conforme número de queries
POSTS_PER_QUERY_LOCAL_ONLINE = {
    1: 6,
    2: 4,
    3: 2,
}

POSTS_PER_QUERY_MIXED = {
    1: 12,
    2: 8,
    3: 4,
}


# ══════════════════════════════════════════════════════════════════════════════
# SSE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _sse_event(content: str) -> str:
    if not content:
        return ""
    payload = json.dumps({"content": content}, ensure_ascii=False)
    return f"data: {payload}\n\n"


def _sse_status(status: str) -> str:
    payload = json.dumps({"status": status}, ensure_ascii=False)
    return f"data: {payload}\n\n"


def _sse_error(message: str) -> str:
    payload = json.dumps({"error": message}, ensure_ascii=False)
    return f"data: {payload}\n\n"


def _sse_done() -> str:
    return "data: [DONE]\n\n"


# ══════════════════════════════════════════════════════════════════════════════
# STATUS MARKER
# ══════════════════════════════════════════════════════════════════════════════

class _Status:
    __slots__ = ('phase',)

    def __init__(self, phase: str):
        self.phase = phase


# ══════════════════════════════════════════════════════════════════════════════
# DETECÇÃO DE MENSAGENS SIMPLES
# ══════════════════════════════════════════════════════════════════════════════

SIMPLE_MESSAGE_PATTERNS = [
    # ── Portuguese ──
    r'^(oi|olá|ola|hey|opa|e aí|eai|fala|eae|e ai)\b',
    r'^(bom dia|boa tarde|boa noite)\s*[!.?]*$',
    r'^(obrigad[oa]?|valeu|vlw|brigad[oa]?|thanks)\s*[!.?]*$',
    r'^(tchau|até logo|ate logo|até mais|ate mais|falou|flw)\s*[!.?]*$',
    r'^(quem é você|quem e voce|o que (é|e) (você|voce)|qual (é|e) seu nome)',
    r'^(como (você|voce) funciona|o que (você|voce) (faz|sabe|pode fazer))',
    r'^(tudo bem|como (você|voce) (está|esta)|como vai|tudo certo|tudo legal)',
    r'^(sim|não|nao|claro|certo|ok|blz|belezinha)\s*[!.?]*$',
    # ── English ──
    r'^(hi|hello|hey|yo|sup|howdy|hola)\b',
    r'^(good morning|good afternoon|good evening|good night)\s*[!.?]*$',
    r'^(thanks|thank you|thx|ty|cheers|appreciate it)\s*[!.?]*$',
    r'^(bye|goodbye|see you|see ya|later|cya|peace out)\s*[!.?]*$',
    r'^(who are you|what are you|what(?:\'s| is) your name)\s*[?.!]*$',
    r'^(how do you work|what can you do|tell me about yourself)\s*[?.!]*$',
    r'^(how are you|how(?:\'s| is) it going|what(?:\'s| is) up|how do you do)',
    r'^(how(?:\'s| is) everything|what(?:\'s| is) new|anything new)',
    r'^(yes|no|sure|ok|okay|cool|nice|great|awesome|right|exactly|alright)\s*[!.?]*$',
    # ── Very short (≤4 chars) ──
    r'^\w{1,4}[?.!]*$',
]

SIMPLE_PATTERN_COMPILED = [re.compile(p, re.IGNORECASE) for p in SIMPLE_MESSAGE_PATTERNS]

NEWS_INDICATOR_WORDS = [
    # Portuguese
    'notícia', 'noticia', 'news', 'aconteceu', 'acontecendo',
    'hoje', 'ontem', 'semana', 'mês', 'ano',
    'brasil', 'mundo', 'política', 'economia', 'eleição',
    'governo', 'presidente', 'resumo', 'artigo', 'feed',
    'último', 'última', 'ultimo', 'ultima', 'recente',
    'sobre', 'pesquisar', 'buscar', 'encontrar',
    'porto alegre', 'são paulo', 'rio de janeiro',
    'enchente', 'tempo', 'clima', 'guerra', 'crise',
    'argentina', 'eua', 'china', 'rússia', 'ucrânia',
    'congresso', 'senado', 'câmara', 'inflação', 'dólar',
    'covid', 'pandemia', 'vacina', 'desemprego',
    'novidades', 'atualidades', 'informações',
    # English
    'happened', 'happening', 'latest', 'recent', 'today',
    'yesterday', 'this week', 'this month',
    'news about', 'tell me about', 'what about',
    'politics', 'economy', 'election', 'war', 'crisis',
    'flood', 'weather', 'climate', 'government',
    'summarize', 'summary', 'explain',
]


def is_simple_message(text: str) -> bool:
    text_clean = text.strip()

    if len(text_clean) <= 4:
        return True

    for pattern in SIMPLE_PATTERN_COMPILED:
        if pattern.search(text_clean):
            logger.info(f"[SIMPLE] Detectada mensagem simples: {text_clean[:50]}")
            return True

    text_lower = text_clean.lower()
    for indicator in NEWS_INDICATOR_WORDS:
        if indicator in text_lower:
            logger.info(f"[SIMPLE] Indicador de notícia '{indicator}' → NÃO é simples")
            return False

    if len(text_clean) <= 20 and '?' not in text_clean:
        logger.info(f"[SIMPLE] Mensagem curta sem '?': {text_clean[:50]}")
        return True

    small_talk_questions = [
        'how are you', 'how r u', 'how are u', 'whats up', "what's up",
        'como vai', 'como esta', 'tudo bem', 'tudo certo',
        'como você está', 'como voce esta',
    ]
    if any(q in text_lower for q in small_talk_questions):
        logger.info(f"[SIMPLE] Pergunta de small-talk: {text_clean[:50]}")
        return True

    return False


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPTS
# ══════════════════════════════════════════════════════════════════════════════

TOOL_CALLING_SYSTEM_PROMPT = """\
Você é um assistente de busca de notícias. Sua ÚNICA função é decidir \
quais buscas realizar na base de notícias para responder à pergunta do usuário.

REGRAS OBRIGATÓRIAS:
1. Você DEVE usar a ferramenta `topic_search` para TODA pergunta que não seja \
saudação ou conversa casual.
2. NUNCA responda à pergunta diretamente — apenas chame a ferramenta de busca.
3. Crie entre 1 e 3 buscas que cubram diferentes ângulos do assunto.
   - 1 busca: para perguntas simples e diretas
   - 2 buscas: para perguntas que envolvem comparação ou múltiplos aspectos
   - 3 buscas: para perguntas complexas que requerem visão panorâmica
4. Use termos descritivos em linguagem natural, no mesmo idioma do usuário.
5. Se o usuário mencionar período ("essa semana", "ontem"), preencha min_days e max_days.
6. Se a pergunta implica atualidades ("o que está acontecendo", "notícias sobre", \
"what is happening"), preencha max_days=30 para priorizar conteúdo recente.
7. Prefira buscas curtas e focadas no tópico (ex: "política brasileira") em vez de \
copiar a pergunta inteira.

IMPORTANTE — formato alternativo:
Se você não conseguir usar a ferramenta de forma estruturada, use EXATAMENTE este \
formato de texto (sem nenhum texto antes ou depois):
[TOOL_CALLS]topic_search{"searches": [{"query": "tópico aqui", "max_days": 14}]}

Exemplos de boas queries:
- "O que está acontecendo na Argentina?" → "Argentina atualidades" com max_days=30 e "crise econômica Argentina" com max_days=30
- "Notícias sobre IA" → "inteligência artificial desenvolvimentos" com max_days=30
- "Política brasileira últimas duas semanas" → "política brasileira" com max_days=14
"""

SYNTHESIS_SYSTEM_PROMPT = """\
Você é o Mota, um assistente de notícias em português brasileiro.

Você receberá uma lista de artigos jornalísticos com título, conteúdo e metadados.
Sua tarefa é:

1. Ler atentamente o conteúdo de cada artigo.
2. Redigir uma resposta clara, fluida e bem organizada em português, resumindo as \
principais informações relevantes para o que o usuário perguntou.
3. NÃO liste os artigos um a um de forma mecânica — sintetize as informações em \
parágrafos coesos.
4. Quando artigos têm datas diferentes, PRIORIZE informações mais recentes. \
Mencione quando algo aconteceu se a data for significativa para o entendimento.
5. Ao final, inclua SEMPRE uma seção "**Fontes**" listando as origens dos artigos usados, \
no formato EXATO:
   - [Nome do veículo — Título do artigo](link)

   Exemplo:
   **Fontes**
   - [Folha de S.Paulo — Governo anuncia novo pacote econômico](https://exemplo.com/noticia1)
   - [G1 — Inflação sobe 0,5% em março](https://exemplo.com/noticia2)

6. Não invente informações. Baseie-se apenas no conteúdo fornecido.
7. Se os artigos não contiverem informação suficiente, diga isso ao usuário.
"""

DIRECT_ARTICLES_SYSTEM_PROMPT = """\
Você é o Mota, um assistente de notícias em português brasileiro.

O usuário selecionou artigos do seu feed de notícias pessoal e os enviou para você.
Cada artigo foi extraído diretamente da sua fonte original (texto completo da página web).

Sua tarefa é:
1. Ler atentamente o conteúdo completo de cada artigo fornecido.
2. Redigir uma síntese clara, fluida e bem organizada em português, destacando os \
pontos mais relevantes e as conexões entre os artigos, quando houver.
3. Sintetize as informações em parágrafos coesos — NÃO liste artigo por artigo \
de forma mecânica.
4. Quando artigos têm datas diferentes, priorize informações mais recentes.
5. Ao final, inclua SEMPRE uma seção "**Fontes**" no formato EXATO:
   - [Nome do veículo — Título do artigo](link)

6. Baseie-se apenas no conteúdo fornecido. Não invente informações.
7. O usuário poderá fazer perguntas de acompanhamento sobre esses artigos — \
mantenha o contexto disponível para a conversa futura.
"""

GENERAL_SYSTEM_PROMPT = """\
Você é o Mota, um assistente de IA especializado em notícias e informações em \
português brasileiro.

Responda às perguntas do usuário de forma clara, útil e educada. Se a pergunta \
não for sobre notícias, responda normalmente como um assistente geral. \
Quando o usuário perguntar sobre você, apresente-se como o Mota, um assistente \
de IA focado em notícias e informações relevantes.

Seja conciso e amigável. Para saudações simples, responda de forma breve e acolhedora.
Responda no mesmo idioma que o usuário usar.
"""


# ══════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITION
# ══════════════════════════════════════════════════════════════════════════════

TOPIC_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "topic_search",
        "description": (
            "Busca notícias recentes na base interna usando NLP semântico. "
            "Você pode criar entre 1 e 3 buscas independentes para cobrir ângulos "
            "diferentes do assunto. "
            "Use palavras-chave descritivas e em linguagem natural, pois a busca é semântica. "
            "Se o usuário mencionar período (ex: 'essa semana', 'ontem'), preencha "
            "min_days e max_days. "
            "Se a pergunta implica atualidades (ex: 'o que está acontecendo', 'notícias sobre'), "
            "preencha max_days=30 para priorizar conteúdo recente. "
            "Prefira buscas em português quando o usuário escrever em português."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "searches": {
                    "type": "array",
                    "description": "Lista de 1 a 3 buscas semânticas. Cada busca é independente.",
                    "minItems": 1,
                    "maxItems": 3,
                    "items": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": (
                                    "Palavras-chave ou frase descritiva para busca semântica. "
                                    "Ex: 'enchentes Rio Grande do Sul', 'eleições Porto Alegre'."
                                ),
                            },
                            "min_days": {
                                "type": "integer",
                                "description": "Artigos publicados há pelo menos N dias.",
                            },
                            "max_days": {
                                "type": "integer",
                                "description": "Artigos publicados há no máximo N dias.",
                            },
                        },
                        "required": ["query"],
                    },
                }
            },
            "required": ["searches"],
        },
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# UTILITÁRIOS DE TEXTO
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

    # Compact format: metadata in one line, content in next
    # Saves ~4 lines per article vs old format ≈ 200+ tokens across 8 articles
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
            # Tenta ISO format (YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS...)
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

    Com half_life=7 e weight=0.4:
      - Artigo de hoje (0 dias):  boost = +0.400
      - Artigo de 7 dias:         boost = +0.200
      - Artigo de 14 dias:        boost = +0.100
      - Artigo de 30 dias:        boost = +0.024
      - Artigo de 90 dias:        boost ≈ 0.001

    Isso garante que, para "What is happening to Trump?", um artigo de hoje
    com similarity 0.65 (boosted: 1.05) supere um artigo de 30 dias com
    similarity 0.85 (boosted: 0.874).
    """
    if not articles:
        return articles

    now = datetime.now(timezone.utc)

    for art in articles:
        raw_score = art.get("similarity_score")
        if raw_score is None:
            # Artigos sem score (ex: online) recebem score neutro
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
            # Sem data: mantém score original, sem boost nem penalidade
            art["similarity_score"] = raw_score
            art["recency_boost"] = 0.0
            art["_age_days"] = None

    # Re-ordena por score boostado (maior primeiro)
    articles.sort(key=lambda a: a.get("similarity_score", 0), reverse=True)

    # Log do ranking
    logger.info(f"[RECENCY] Ranking após boost (half_life={half_life}, weight={weight}):")
    for i, art in enumerate(articles[:10], 1):
        raw = art.get("similarity_score_raw", 0)
        boosted = art.get("similarity_score", 0)
        boost = art.get("recency_boost", 0)
        age = art.get("_age_days", "?")
        title = art.get("title", "")[:60]
        logger.info(
            f"  {i}. score {raw:.3f}→{boosted:.3f} (+{boost:.3f}) "
            f"age={age}d | {title}"
        )

    return articles


# ══════════════════════════════════════════════════════════════════════════════
# DEDUPLICAÇÃO DE ARTIGOS
# ══════════════════════════════════════════════════════════════════════════════

def _normalize_url(url: str) -> str:
    """Normaliza URL para comparação de duplicatas."""
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
    budget: int = TOTAL_CONTEXT_CHAR_LIMIT,
) -> list[dict]:
    """
    Aplica orçamento total de contexto, truncando artigos menos relevantes.

    Artigos já estão ordenados por score boostado (melhores primeiro).
    Os primeiros recebem conteúdo completo; os últimos podem ser truncados
    se o orçamento for excedido.

    Isso economiza tokens na API sem sacrificar qualidade dos artigos
    mais relevantes.
    """
    if not articles:
        return articles

    total = sum(len(a.get("description", "")) for a in articles)

    if total <= budget:
        logger.info(f"[BUDGET] Conteúdo total {total} chars ≤ orçamento {budget}")
        return articles

    logger.info(f"[BUDGET] Conteúdo total {total} chars > orçamento {budget} — truncando...")

    remaining = budget
    min_per_article = 400  # Mínimo para manter artigo útil

    for i, art in enumerate(articles):
        desc = art.get("description", "")
        desc_len = len(desc)

        if desc_len <= remaining:
            remaining -= desc_len
        elif remaining > min_per_article:
            art["description"] = desc[:remaining] + "\n[...]"
            remaining = 0
        else:
            # Orçamento esgotado — truncar para o mínimo
            if desc_len > min_per_article:
                art["description"] = desc[:min_per_article] + "\n[...]"
            # Se já é curto, mantém como está

    final_total = sum(len(a.get("description", "")) for a in articles)
    logger.info(f"[BUDGET] Resultado: {total} → {final_total} chars")


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

        # Apenas artigos locais que ainda não foram lidos
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
# DETECÇÃO DE RECÊNCIA IMPLÍCITA
# ══════════════════════════════════════════════════════════════════════════════

_IMPLICIT_RECENCY_PATTERNS = [
    # Portuguese — implica eventos atuais
    re.compile(r'o que (?:está|estão) (?:acontecendo|ocorrendo)', re.I),
    re.compile(r'o que (?:há|tem) de (?:novo|novidade)', re.I),
    re.compile(r'últimas?\s+(?:notícias?|informações?|novidades?)', re.I),
    re.compile(r'notícias?\s+(?:recentes?|de hoje|da semana|do dia)', re.I),
    re.compile(r'(?:como\s+)?está\s+(?:a\s+)?(?:situação|crise|guerra|economia)', re.I),
    re.compile(r'(?:o que |o q )(?:ta|tá|está) (?:rolando|rolando|bombando)', re.I),
    re.compile(r'(?:novidades?|atualidades?)\s+(?:sobre|de|do|da)', re.I),
    re.compile(r'me (?:atualiza|atualize)|(?:atualização|update)', re.I),
    # English — implies current events
    re.compile(r"what(?:'s| is) happening", re.I),
    re.compile(r"what(?:'s| is) (?:the latest|new|going on)", re.I),
    re.compile(r'latest\s+(?:news|updates?|developments?|info)', re.I),
    re.compile(r'current\s+(?:events|situation|status|news|state)', re.I),
    re.compile(r'(?:any|recent)\s+(?:news|updates?|developments?)', re.I),
    re.compile(r'(?:what is|what\'s) (?:going on|up) (?:with|in|on)', re.I),
    re.compile(r'tell me (?:the )?latest (?:about|on|in)', re.I),
]


def _has_implicit_recency(text: str) -> bool:
    """
    Detecta se a pergunta implica atualidades mesmo sem menção
    explícita de tempo.

    Exemplos:
      - "What is happening to Trump?"       → True
      - "O que está acontecendo na Ucrânia?" → True
      - "Who is Albert Einstein?"            → False
      - "Como funciona a fotossíntese?"      → False
    """
    for pattern in _IMPLICIT_RECENCY_PATTERNS:
        if pattern.search(text):
            return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
# BUSCA LOCAL
# ══════════════════════════════════════════════════════════════════════════════

def _call_local(
    query: str,
    limit: int,
    min_days: Optional[int],
    max_days: Optional[int],
) -> list[dict]:
    """Executa busca local na base de feeds do usuário."""
    logger.info(
        f"[LOCAL] search_articles_by_text({query!r}, limit={limit}, "
        f"min_days={min_days}, max_days={max_days})"
    )

    try:
        results = search_articles_by_text(
            query=query,
            limit=limit,
            min_similarity=SEARCH_THRESHOLD,
            min_days=min_days,
            max_days=max_days,
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
    """Normaliza lista de buscas para garantir formato consistente."""
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
    """Calcula distribuição de posts local/online por query."""
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
    """
    searches = _normalize_searches(searches)
    num_queries = len(searches)

    local_per, online_per = _get_posts_distribution(num_queries, source_mode)

    logger.info(f"\n{'='*70}")
    logger.info(f"[SEARCH] Iniciando buscas")
    logger.info(f"[SEARCH] Queries: {num_queries}  |  Modo: {source_mode}  |  Deep: {deep_reading}")
    logger.info(f"[SEARCH] Distribuição por query → Local: {local_per}  Online: {online_per}")
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
            local_results = _call_local(query, local_per, min_days, max_days)
            local_cut = local_results[:local_per]

            for art in local_cut:
                art["search_type"] = art.get("search_type", "local")
                if art.get("description"):
                    art["description"] = _truncate_content(_strip_html(art["description"]))

            all_articles.extend(local_cut)
            logger.info(f"  [LOCAL] {len(local_cut)} artigos")

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
                logger.info(f"  [ONLINE] {len(online_cut)} artigos")
            except Exception as e:
                logger.error(f"  [ONLINE] ✗ Erro: {e}")

    # ── Fase 2: Pipeline de pós-processamento ──────────────────────────────

    # 2a. Deduplicação por URL
    all_articles = _deduplicate_articles(all_articles)

    # 2b. Recency boost — prioriza artigos recentes
    all_articles = _apply_recency_boost(all_articles)

    # 2c. Deep reading seletivo (apenas top N artigos locais)
    if deep_reading:
        all_articles = _selective_deep_read(all_articles)

    # 2d. Orçamento de contexto — trunca artigos menos relevantes
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
            f"  [{idx}]{deep_tag} {source} | raw={raw_score:.3f} "
            f"boosted={boosted_score:.3f} (+{boost:.3f}) age={age}d | "
            f"{art.get('feed_title', '')} | {art.get('title', '')}"
        )
        logger.info(f"       ({len(desc)} chars): {desc[:120]}{'...' if len(desc) > 120 else ''}")

    logger.info(f"{'='*70}\n")

    if not all_articles:
        return "Nenhum artigo encontrado para os tópicos pesquisados.", []

    # ── Fase 4: Formatação compacta para o LLM ────────────────────────────
    blocks = [
        "A seguir estão os artigos encontrados, ordenados por relevância e recência. "
        "Leia o conteúdo de cada um e redija sua resposta:\n"
    ]

    for idx, article in enumerate(all_articles, 1):
        blocks.append(_format_article_for_llm(idx, article))

    return "\n\n".join(blocks), all_articles


# ══════════════════════════════════════════════════════════════════════════════
# DETECÇÃO DE TOOL CALLS EM FORMATO TEXTO
# ══════════════════════════════════════════════════════════════════════════════

_RE_TEXT_TOOL_CALL = re.compile(
    r'^\[TOOL_CALLS\](\w+)\s*(\{.*\})\s*$',
    re.DOTALL,
)


def _try_parse_text_tool_call(content: str) -> Optional[tuple[str, str]]:
    """Detecta e parseia tool calls em formato texto."""
    if not content:
        return None

    content_stripped = content.strip()
    match = _RE_TEXT_TOOL_CALL.match(content_stripped)

    if not match:
        return None

    tool_name = match.group(1)
    raw_args = match.group(2)

    if HAS_JSON_REPAIR:
        try:
            repaired = repair_json(raw_args)
            json.loads(repaired)
            raw_args = repaired
            logger.info(f"[TEXT_TOOL] JSON reparado com sucesso")
        except Exception:
            logger.warning(f"[TEXT_TOOL] json_repair falhou")

    return tool_name, raw_args


# ══════════════════════════════════════════════════════════════════════════════
# EXTRAÇÃO DE RESTRIÇÕES DE TEMPO
# ══════════════════════════════════════════════════════════════════════════════

_TIME_PATTERNS: list[tuple[re.Pattern, Optional[int]]] = [
    # Portuguese
    (re.compile(r'(?:últimas?\s+)?duas\s+últimas?\s+semanas', re.I), 14),
    (re.compile(r'últimas?\s+duas\s+semanas', re.I), 14),
    (re.compile(r'(?:esta|essa|nesta|nessa)\s+semana', re.I), 7),
    (re.compile(r'última\s+semana', re.I), 7),
    (re.compile(r'\bontem\b', re.I), 1),
    (re.compile(r'\bhoje\b', re.I), 0),
    (re.compile(r'últimos?\s+(\d+)\s+dias?', re.I), None),
    (re.compile(r'últimas?\s+(\d+)\s+semanas?', re.I), None),
    (re.compile(r'últimos?\s+(\d+)\s+mes(?:es)?', re.I), None),
    (re.compile(r'último\s+mês', re.I), 30),
    (re.compile(r'(?:este|esse)\s+mês', re.I), 30),
    (re.compile(r'(?:este|esse)\s+ano', re.I), 365),
    (re.compile(r'último\s+ano', re.I), 365),
    # English
    (re.compile(r'(?:this|last)\s+week', re.I), 7),
    (re.compile(r'(?:this|last)\s+month', re.I), 30),
    (re.compile(r'(?:this|last)\s+year', re.I), 365),
    (re.compile(r'last\s+(\d+)\s+days?', re.I), None),
    (re.compile(r'last\s+(\d+)\s+weeks?', re.I), None),
    (re.compile(r'last\s+(\d+)\s+months?', re.I), None),
    (re.compile(r'\byesterday\b', re.I), 1),
    (re.compile(r'\btoday\b', re.I), 0),
]

_TIME_MULTIPLIERS = {
    'dia': 1, 'dias': 1,
    'semana': 7, 'semanas': 7,
    'mês': 30, 'mes': 30, 'meses': 30,
    'ano': 365, 'anos': 365,
    'day': 1, 'days': 1,
    'week': 7, 'weeks': 7,
    'month': 30, 'months': 30,
    'year': 365, 'years': 365,
}


def _extract_time_constraint(text: str) -> tuple[Optional[int], Optional[int]]:
    """Extrai restrição de tempo (max_days) a partir de expressões no texto."""
    for pattern, days in _TIME_PATTERNS:
        match = pattern.search(text)
        if match:
            if days is not None:
                return None, days

            num = int(match.group(1))
            matched_text = match.group(0).lower()

            for unit, mult in _TIME_MULTIPLIERS.items():
                if unit in matched_text:
                    return None, num * mult

            return None, num

    return None, None


# ══════════════════════════════════════════════════════════════════════════════
# EXTRAÇÃO DE TÓPICO CENTRAL
# ══════════════════════════════════════════════════════════════════════════════

_QUESTION_PREFIXES = [
    # Portuguese
    r'^quais?\s+(são|é|foram|foi)\s+(as|os|a|o)?\s*'
    r'(novidades|últimas|notícias|mudanças|atualizações|informações)\s*(de|do|da|dos|das|sobre|em|no|na)?\s*',
    r'^quais?\s+(são|é|foram|foi)\s+(as|os|a|o)?\s*',
    r'^qual\s+(é|foi|será|seria)\s+(a|o)?\s*',
    r'^o que (está|estão|é|são|foi|foram)\s+(acontecendo|ocorrendo)\s+(com|no|na|em|n[oa]s)?\s*',
    r'^o que (há|tem|existe)\s+(de|em|no|na|sobre|para)\s*',
    r'^o que (está|é|estão|são)\s+',
    r'^o que se sabe\s+(sobre|de|do|da)\s*',
    r'^quando\s+', r'^onde\s+', r'^como\s+', r'^por que\s+', r'^porque\s+',
    r'^me (fale|diga|conte|mostre|explique|resuma)\s+(sobre|a respeito de|mais sobre)\s*',
    r'^quero (saber|ler|ver|entender|conhecer)\s+(sobre|a respeito de|mais sobre)\s*',
    r'^pode\s+(me\s+)?(falar|dizer|contar|mostrar|explicar|resumir)\s+(sobre|a respeito de)?\s*',
    r'^você\s+(pode|sabe|tem|conhece)\s+(me\s+)?(falar|dizer|contar|mostrar|explicar|resumir)\s+(sobre|a respeito de)?\s*',
    r'^notícias?\s+(sobre|de|do|da|dos|das)\s*',
    r'^resumo\s+(sobre|de|do|da|dos|das)\s*',
    r'^há\s+(alguma|novas|algumas)\s+(notícia|informação|novidade)\s+(sobre|de|do|da)?\s*',
    r'^tem\s+(alguma|novas|algumas)\s*(notícia|informação|novidade)\s+(sobre|de|do|da)?\s*',
    # English
    r"^what(?:'s| is)\s+(happening|going on)\s+(in|with|on)?\s*",
    r"^what(?:'s| is)\s+(the\s+)?latest\s+(on|about|from|in)?\s*",
    r"^what(?:'s| is)\s+(new|going on)\s+(with|in|about)?\s*",
    r"^what\s+(is|are|was|were|has|have|do|does|did|can|could|will|would|should)\s+",
    r"^which\s+(is|are|was|were|has|have)\s+",
    r"^tell me about\s+",
    r"^news about\s+",
    r"^latest (on|about|from)\s+",
    r"^any (news|updates?|information)\s+(on|about|from|regarding)?\s*",
]

_QUESTION_PREFIX_COMPILED = [re.compile(p, re.IGNORECASE) for p in _QUESTION_PREFIXES]

_TIME_SUFFIXES = [
    re.compile(r'\s*(?:nessas?|estas?|nestas?|n[oa]s)\s+últimas?\s*', re.I),
    re.compile(r'\s*(?:últimas?|último)\s*', re.I),
    re.compile(r'\s*recentemente\s*', re.I),
    re.compile(r'\s*atualmente\s*', re.I),
    re.compile(r'\s*agora\s*', re.I),
    re.compile(r'\s*(?:esta|essa|nesta|nessa)\s+(semana|mês|ano)\s*', re.I),
    re.compile(r'\s*(?:últimas?\s+)?(?:duas|três|quatro|cinco|seis|sete|oito|nove|dez)\s+semanas?\s*', re.I),
    re.compile(r'\s*(?:últimos?\s+)?\d+\s+(?:dias|semanas|meses|anos)\s*', re.I),
    re.compile(r'\s*(?:this|last)\s+(?:week|month|year)\s*', re.I),
    re.compile(r'\s*recently\s*', re.I),
    re.compile(r'\s*currently\s*', re.I),
]


def _extract_topic(text: str) -> str:
    """Extrai o tópico central de uma pergunta."""
    topic = text.strip().rstrip('?!.').strip()

    for pattern in _QUESTION_PREFIX_COMPILED:
        m = pattern.match(topic)
        if m:
            topic = topic[m.end():].strip()
            break

    for pattern in _TIME_SUFFIXES:
        topic = pattern.sub(' ', topic).strip()

    topic = re.sub(
        r'\s+(?:de|do|da|dos|das|em|no|na|nos|nas|com|por|para|sobre)\s*$',
        '', topic, flags=re.IGNORECASE,
    )

    topic = re.sub(r'\s{2,}', ' ', topic).strip()
    topic = topic.rstrip('?!.,;:')

    return topic


# ══════════════════════════════════════════════════════════════════════════════
# GERAÇÃO DE QUERIES FALLBACK
# ══════════════════════════════════════════════════════════════════════════════

def _generate_fallback_searches(text: str) -> list[dict]:
    """
    Gera queries de busca quando o LLM não chamou a ferramenta.

    Detecta tanto restrições de tempo explícitas quanto implícitas.
    Perguntas como "What is happening to Trump?" receberão max_days=30
    automaticamente, mesmo sem menção explícita de tempo.
    """
    min_days, max_days = _extract_time_constraint(text)

    # ── Detecção de recência implícita ──────────────────────────────────────
    # Se não há restrição de tempo explícita, mas a pergunta implica
    # atualidades, aplicar max_days padrão
    if max_days is None and _has_implicit_recency(text):
        max_days = IMPLICIT_RECENCY_MAX_DAYS
        logger.info(
            f"[FALLBACK] Recência implícita detectada → max_days={max_days}"
        )

    topic = _extract_topic(text)
    searches: list[dict] = []

    # Caso 1: tópico extraído com sucesso
    if topic and len(topic) > 2 and topic.lower() != text.strip().lower().rstrip('?!$.'):
        entry: dict = {"query": topic}
        if max_days is not None:
            entry["max_days"] = max_days
        if min_days is not None:
            entry["min_days"] = min_days
        searches.append(entry)

        # Quebra tópicos compostos
        for sep in [' e ', ', ', '; ']:
            if sep in topic:
                parts = [p.strip() for p in topic.split(sep) if len(p.strip()) > 3]
                for part in parts[:2]:
                    sub: dict = {"query": part}
                    if max_days is not None:
                        sub["max_days"] = max_days
                    if min_days is not None:
                        sub["min_days"] = min_days
                    searches.append(sub)
                break

        # Se só temos 1 busca, adiciona variante
        if len(searches) == 1:
            variant: dict = {"query": f"{topic} atualidades"}
            if max_days is not None:
                variant["max_days"] = max_days
            searches.append(variant)

    # Caso 2: limpeza agressiva
    else:
        cleaned = text.strip().rstrip('?!$.')
        for pat in [
            r'^quais são as novidades\s+(?:da|do|de|dos|das)?\s*',
            r'^o que está acontecendo\s+(?:com|no|na|em|n[oa]s)?\s*',
            r'^me fale sobre\s+',
            r'^notícias sobre\s+',
        ]:
            cleaned = re.sub(pat, '', cleaned, flags=re.IGNORECASE).strip()

        if cleaned and len(cleaned) > 2:
            entry = {"query": cleaned}
            if max_days is not None:
                entry["max_days"] = max_days
            searches.append(entry)

        if not searches:
            entry = {"query": text.strip().rstrip('?!$.')}
            if max_days is not None:
                entry["max_days"] = max_days
            searches.append(entry)

    logger.info(f"[FALLBACK] Tópico: '{topic}'  |  Tempo: min={min_days} max={max_days}")
    for i, s in enumerate(searches, 1):
        logger.info(f"[FALLBACK] Query {i}: {s}")

    return searches[:3]


# ══════════════════════════════════════════════════════════════════════════════
# PARSING DE TOOL ARGUMENTS
# ══════════════════════════════════════════════════════════════════════════════

_RE_QUERY = re.compile(r"""(?:"query"|'query')\s*:\s*(?:"([^"]+)"|'([^']+)')""")
_RE_MAX_DAYS = re.compile(r"""(?:"max_days"|'max_days')\s*:\s*(\d+)""")
_RE_MIN_DAYS = re.compile(r"""(?:"min_days"|'min_days')\s*:\s*(\d+)""")


def _extract_searches_regex(text: str) -> list[dict]:
    """Extrai buscas via regex (fallback de parsing)."""
    searches: list[dict] = []

    for m in _RE_QUERY.finditer(text):
        query_val = m.group(1) or m.group(2)
        entry: dict = {"query": query_val}

        nearby = text[m.start():m.start() + 150]
        mx = _RE_MAX_DAYS.search(nearby)
        mn = _RE_MIN_DAYS.search(nearby)

        if mx:
            entry["max_days"] = int(mx.group(1))
        if mn:
            entry["min_days"] = int(mn.group(1))

        searches.append(entry)

    return searches


def _parse_tool_arguments(raw: str) -> dict:
    """Parseia argumentos de tool call (JSON ou formato alternativo)."""
    parsed = None

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning(f"[PARSE] JSON inválido: {e}")

    if parsed is None and HAS_JSON_REPAIR:
        try:
            parsed = json.loads(repair_json(raw))
            logger.info(f"[PARSE] ✓ JSON reparado")
        except Exception as err:
            logger.error(f"[PARSE] json_repair falhou: {err}")

    if parsed is None:
        searches = _extract_searches_regex(raw)
        if searches:
            logger.warning(f"[PARSE] ✓ {len(searches)} queries via regex")
            return {"searches": searches}
        return {"searches": []}

    if isinstance(parsed, dict) and "searches" in parsed:
        searches = parsed["searches"]

        if isinstance(searches, str):
            try:
                searches = json.loads(searches)
            except json.JSONDecodeError:
                if HAS_JSON_REPAIR:
                    try:
                        searches = json.loads(repair_json(searches))
                    except Exception:
                        pass

            if isinstance(searches, str):
                try:
                    searches = ast.literal_eval(searches)
                except (ValueError, SyntaxError):
                    pass

            if isinstance(searches, str):
                searches = _extract_searches_regex(searches) or []

            parsed["searches"] = searches

        if isinstance(parsed["searches"], list):
            validated = []
            for item in parsed["searches"]:
                if isinstance(item, dict):
                    validated.append(item)
                elif isinstance(item, str):
                    try:
                        parsed_item = json.loads(item)
                    except json.JSONDecodeError:
                        try:
                            parsed_item = ast.literal_eval(item)
                        except (ValueError, SyntaxError):
                            parsed_item = None

                    if isinstance(parsed_item, dict):
                        validated.append(parsed_item)
                    else:
                        validated.append({"query": item})

            parsed["searches"] = validated

    return parsed


def _serialize_assistant_message(message) -> dict:
    """Serializa mensagem do assistente para formato de conversa."""
    content = getattr(message, 'content', None) or ""
    result = {"role": "assistant", "content": content}

    tool_calls = getattr(message, 'tool_calls', None)
    if tool_calls:
        serialized_tcs = []
        for tc in tool_calls:
            fn = getattr(tc, 'function', None)
            tc_dict = {
                "id": getattr(tc, 'id', ''),
                "type": "function",
                "function": {
                    "name": getattr(fn, 'name', '') if fn else '',
                    "arguments": getattr(fn, 'arguments', '') if fn else '',
                },
            }
            serialized_tcs.append(tc_dict)
        result["tool_calls"] = serialized_tcs

    return result


# ══════════════════════════════════════════════════════════════════════════════
# HANDLER DE ARTIGOS DIRETOS DO FEED
# ══════════════════════════════════════════════════════════════════════════════

def _handle_direct_articles(
    user_message: str,
    articles: list[dict],
) -> Iterator:
    """Processa artigos enviados diretamente pelo usuário."""
    logger.info(f"[DIRECT] Processando {len(articles)} artigos diretos do feed")

    yield _Status("reading")

    # Enriquece com leitura profunda
    enriched: list[dict] = []
    for raw_article in articles:
        art = dict(raw_article)

        if art.get("description"):
            art["description"] = _truncate_content(_strip_html(art["description"]))

        art = _enrich_with_full_text(art)
        enriched.append(art)

        deep_tag = " [✓ deep]" if art.get("deep_read") else " [✗ sem extração]"
        desc_len = len(_strip_html(art.get("description", "")))
        logger.info(f"  → {art.get('title', '')}{deep_tag} ({desc_len} chars)")

    # Aplica orçamento de contexto nos artigos diretos também
    enriched = _apply_context_budget(enriched)

    yield _Status("synthesizing")

    blocks = [
        "O usuário selecionou os seguintes artigos do seu feed pessoal. "
        "O texto completo de cada artigo foi extraído diretamente da fonte original. "
        "Leia cada um com atenção e produza uma síntese detalhada:\n"
    ]

    for idx, article in enumerate(enriched, 1):
        blocks.append(_format_article_for_llm(idx, article))

    articles_context = "\n\n".join(blocks)

    messages = [
        {"role": "system", "content": DIRECT_ARTICLES_SYSTEM_PROMPT},
        {"role": "user", "content": f"{user_message}\n\n{articles_context}"},
    ]

    chunk_count = 0
    for chunk in stream_llm_response(messages):
        chunk_count += 1
        yield chunk

    logger.info(f"[DIRECT] ✓ Concluído: {chunk_count} chunks enviados")


# ══════════════════════════════════════════════════════════════════════════════
# FALLBACK DE BUSCA DIRETA
# ══════════════════════════════════════════════════════════════════════════════

def _fallback_search_and_synthesize(
    user_message: str,
    source_mode: str,
    deep_reading: bool,
) -> Iterator:
    """Executa busca direta quando LLM não chamou ferramenta."""
    logger.info(f"[FALLBACK] Iniciando busca direta")

    searches = _generate_fallback_searches(user_message)
    yield _Status("searching")

    articles_text, all_articles = run_searches(
        searches,
        source_mode=source_mode,
        deep_reading=deep_reading,
    )

    if not all_articles:
        logger.warning("[FALLBACK] Nenhum artigo encontrado")
        yield _Status("thinking")

        msgs = [
            {"role": "system", "content": GENERAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        chunk_count = 0
        for chunk in stream_llm_response(msgs):
            chunk_count += 1
            yield chunk

        logger.info(f"[FALLBACK] ✓ Resposta geral: {chunk_count} chunks")
        return

    yield _Status("synthesizing")

    messages = [
        {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
        {"role": "user", "content": f"{user_message}\n\n{articles_text}"},
    ]

    chunk_count = 0
    for chunk in stream_llm_response(messages):
        chunk_count += 1
        yield chunk

    logger.info(f"[FALLBACK] ✓ Síntese concluída: {chunk_count} chunks")


# ══════════════════════════════════════════════════════════════════════════════
# HANDLER PRINCIPAL (RAW)
# ══════════════════════════════════════════════════════════════════════════════

def _generate_chat_stream(chat_request, user) -> Iterator:
    """Handler principal do chat (retorna chunks sem formatação SSE)."""
    logger.info(f"\n{'#'*70}")
    logger.info(f"[CHAT] Usuário: {user.get('username', user)}")
    logger.info(f"[CHAT] Mensagem: {chat_request.message!r}")

    source_mode = getattr(chat_request, "source_mode", "local")
    deep_reading = getattr(chat_request, "deep_reading", False)
    user_message = chat_request.message

    # ── CASO 1: Artigos diretos do feed ──────────────────────────────────────
    raw_articles = getattr(chat_request, "articles", None) or []
    direct_articles = [
        a.model_dump() if hasattr(a, "model_dump") else dict(a)
        for a in raw_articles
    ]

    if direct_articles:
        logger.info(f"[CHAT] Modo: artigos diretos ({len(direct_articles)} artigos)")
        yield from _handle_direct_articles(user_message, direct_articles)
        return

    logger.info(f"[CHAT] Modo: {source_mode}  |  Deep: {deep_reading}")
    logger.info(f"{'#'*70}")

    # ── CASO 2: Mensagem simples (sem busca) ─────────────────────────────────
    if is_simple_message(user_message):
        logger.info("[CHAT] → Mensagem simples: resposta direta")
        yield _Status("thinking")

        msgs = [
            {"role": "system", "content": GENERAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        chunk_count = 0
        for chunk in stream_llm_response(msgs):
            chunk_count += 1
            yield chunk

        logger.info(f"[CHAT] ✓ Resposta simples: {chunk_count} chunks")
        return

    # ── CASO 3: Mensagem que requer informação ───────────────────────────────
    yield _Status("searching")

    # ── 3a. Tentativa de tool calling ────────────────────────────────────────
    tool_call_failed = False
    initial_response = None

    try:
        initial_response = call_llm_with_tools(
            user_message,
            [TOPIC_SEARCH_TOOL],
            system_prompt=TOOL_CALLING_SYSTEM_PROMPT,
            tool_choice="auto",
            max_tokens=1024,
            temperature=0.2,
        )
    except Exception as e:
        logger.error(f"[CHAT] ✗ Erro em call_llm_with_tools: {e}", exc_info=True)
        tool_call_failed = True

    # ── 3b. Verificar tool calls estruturados ─────────────────────────────────
    has_tool_calls = False
    message = None

    if initial_response is not None:
        try:
            message = initial_response.choices[0].message
            tc = getattr(message, 'tool_calls', None)
            has_tool_calls = tc is not None and len(tc) > 0

            content_preview = repr(getattr(message, 'content', '') or '')[:120]
            logger.info(
                f"[CHAT] Resposta LLM: role={getattr(message, 'role', '?')}  "
                f"tool_calls={has_tool_calls}  content={content_preview}"
            )
        except (IndexError, AttributeError) as e:
            logger.error(f"[CHAT] ✗ Erro ao processar resposta: {e}", exc_info=True)
            tool_call_failed = True

    # ── 3c. Detectar tool calls em formato texto ─────────────────────────────
    if not has_tool_calls and message is not None and not tool_call_failed:
        content = getattr(message, 'content', '') or ''
        text_tool = _try_parse_text_tool_call(content)

        if text_tool is not None:
            tool_name, raw_args = text_tool
            logger.info(f"[CHAT] ✓ Tool call em TEXTO: {tool_name}")

            if tool_name == "topic_search":
                arguments = _parse_tool_arguments(raw_args)
                searches = arguments.get("searches", [])

                # Aplica recência implícita nas buscas extraídas do text-tool
                if _has_implicit_recency(user_message):
                    for s in searches:
                        if "max_days" not in s:
                            s["max_days"] = IMPLICIT_RECENCY_MAX_DAYS
                    logger.info(
                        f"[CHAT] Recência implícita aplicada às {len(searches)} "
                        f"buscas (max_days={IMPLICIT_RECENCY_MAX_DAYS})"
                    )

                if searches:
                    logger.info(f"[CHAT] Buscas do text-tool-call:")
                    for i, s in enumerate(searches, 1):
                        logger.info(f"  {i}. {s}")

                    articles_text, all_articles = run_searches(
                        searches,
                        source_mode=source_mode,
                        deep_reading=deep_reading,
                    )

                    if all_articles:
                        yield _Status("synthesizing")

                        messages = [
                            {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                            {"role": "user", "content": f"{user_message}\n\n{articles_text}"},
                        ]

                        chunk_count = 0
                        for chunk in stream_llm_response(messages):
                            chunk_count += 1
                            yield chunk

                        logger.info(f"[CHAT] ✓ Text-tool síntese: {chunk_count} chunks")
                        return

    # ── 3d. Sem tool calls → FALLBACK ────────────────────────────────────────
    if not has_tool_calls:
        reason = "erro na chamada" if tool_call_failed else "modelo não chamou"
        logger.info(f"[CHAT] → Fallback ({reason})")
        yield from _fallback_search_and_synthesize(user_message, source_mode, deep_reading)
        return

    # ── 3e. Processa tool calls estruturados ──────────────────────────────────
    logger.info(f"[CHAT] ✓ Tool calls estruturados: {len(message.tool_calls)}")

    all_articles: list[dict] = []
    tool_results: list[dict] = []

    for tc_idx, tool_call in enumerate(message.tool_calls):
        fn_name = tool_call.function.name
        logger.info(f"[CHAT] Tool call [{tc_idx}]: {fn_name!r}")

        if fn_name != "topic_search":
            logger.warning(f"[CHAT] ✗ Tool desconhecida: {fn_name!r}")
            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": "Ferramenta não suportada.",
            })
            continue

        arguments = _parse_tool_arguments(tool_call.function.arguments)
        searches = arguments.get("searches", [])

        # Aplica recência implícita nas buscas do tool call estruturado
        if _has_implicit_recency(user_message):
            for s in searches:
                if "max_days" not in s:
                    s["max_days"] = IMPLICIT_RECENCY_MAX_DAYS
            logger.info(
                f"[CHAT] Recência implícita aplicada às {len(searches)} "
                f"buscas (max_days={IMPLICIT_RECENCY_MAX_DAYS})"
            )

        if not searches:
            logger.warning(f"[CHAT] ✗ Sem buscas em tool_call[{tc_idx}]")
            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": "Nenhuma busca encontrada.",
            })
            continue

        logger.info(f"[CHAT] Buscas da IA:")
        for i, s in enumerate(searches, 1):
            logger.info(f"  {i}. {s}")

        articles_text, raw_arts = run_searches(
            searches,
            source_mode=source_mode,
            deep_reading=deep_reading,
        )

        all_articles.extend(raw_arts)

        tool_results.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": articles_text,
        })

    # Sem artigos → fallback
    if not all_articles:
        logger.warning("[CHAT] ✗ Nenhum artigo via tool calls → fallback")
        yield from _fallback_search_and_synthesize(user_message, source_mode, deep_reading)
        return

    # ── 3f. Síntese final ─────────────────────────────────────────────────────
    yield _Status("synthesizing")

    messages = [
        {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
        _serialize_assistant_message(message),
        *tool_results,
    ]

    logger.info(
        f"[CHAT] Síntese final: {len(tool_results)} tool_results  "
        f"{len(all_articles)} artigos  {len(messages)} msgs"
    )

    chunk_count = 0
    for chunk in stream_llm_response(messages):
        chunk_count += 1
        yield chunk

    logger.info(f"[CHAT] ✓ Síntese concluída: {chunk_count} chunks")


def receive(chat_request, user) -> Iterator[str]:
    """
    Handler principal do chat com formatação SSE.

    Args:
        chat_request: Request com mensagem e configurações
        user: Dados do usuário

    Yields:
        Eventos SSE formatados
    """
    try:
        for chunk in _generate_chat_stream(chat_request, user):
            if isinstance(chunk, _Status):
                yield _sse_status(chunk.phase)
            else:
                event = _sse_event(chunk)
                if event:
                    yield event
    except Exception as e:
        logger.error(f"[CHAT] ✗ Erro não tratado: {e}", exc_info=True)
        yield _sse_error(str(e))

    yield _sse_done()
