"""
mota/chat_query_parser.py — NLP pattern extraction and fallback search generation.

Handles:
  - Implicit recency detection (e.g. "what's happening" → max_days=30)
  - Time constraint extraction from natural language
  - Topic extraction from user messages
  - Fallback search generation when the LLM doesn't call tools
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from mota.chat_config import IMPLICIT_RECENCY_MAX_DAYS

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# DETECÇÃO DE RECÊNCIA IMPLÍCITA
# ══════════════════════════════════════════════════════════════════════════════

_IMPLICIT_RECENCY_PATTERNS = [
    re.compile(r'o que (?:está|estão) (?:acontecendo|ocorrendo)', re.I),
    re.compile(r'o que (?:há|tem) de (?:novo|novidade)', re.I),
    re.compile(r'últimas?\s+(?:notícias?|informações?|novidades?)', re.I),
    re.compile(r'notícias?\s+(?:recentes?|de hoje|da semana|do dia)', re.I),
    re.compile(r'(?:como\s+)?está\s+(?:a\s+)?(?:situação|crise|guerra|economia)', re.I),
    re.compile(r'(?:o que |o q )(?:ta|tá|está) (?:rolando|rolando|bombando)', re.I),
    re.compile(r'(?:novidades?|atualidades?)\s+(?:sobre|de|do|da)', re.I),
    re.compile(r'me (?:atualiza|atualize)|(?:atualização|update)', re.I),
    re.compile(r"what(?:'s| is) happening", re.I),
    re.compile(r"what(?:'s| is) (?:the latest|new|going on)", re.I),
    re.compile(r'latest\s+(?:news|updates?|developments?|info)', re.I),
    re.compile(r'current\s+(?:events|situation|status|news|state)', re.I),
    re.compile(r'(?:any|recent)\s+(?:news|updates?|developments?)', re.I),
    re.compile(r"(?:what is|what's) (?:going on|up) (?:with|in|on)", re.I),
    re.compile(r'tell me (?:the )?latest (?:about|on|in)', re.I),
]


def _has_implicit_recency(text: str) -> bool:
    """
    Detecta se a pergunta implica atualidades mesmo sem menção
    explícita de tempo.

    Exemplos:
    - "What is happening to Trump?" → True
    - "O que está acontecendo na Ucrânia?" → True
    - "Who is Albert Einstein?" → False
    - "Como funciona a fotossíntese?" → False
    """
    for pattern in _IMPLICIT_RECENCY_PATTERNS:
        if pattern.search(text):
            return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
# EXTRAÇÃO DE RESTRIÇÃO DE TEMPO
# ══════════════════════════════════════════════════════════════════════════════

_TIME_PATTERNS = [
    (re.compile(r'(?:últim[oa]s?|last|past)\s+(\d+)\s+(?:dia|dias|days?)', re.I), 1),
    (re.compile(r'(?:últim[oa]s?|last|past)\s+(\d+)\s+(?:semana|semanas|weeks?)', re.I), 7),
    (re.compile(r'(?:últim[oa]s?|last|past)\s+(\d+)\s+(?:mês|meses|month|months?)', re.I), 30),
    (re.compile(r'(?:últim[oa]s?|last|past)\s+(\d+)\s+(?:ano|anos|year|years?)', re.I), 365),
    (re.compile(r'(?:hoje|today|agora|now)\b', re.I), 0),
    (re.compile(r'(?:ontem|yesterday)\b', re.I), 1),
    (re.compile(r'(?:esta|this)\s+(?:semana|week)', re.I), 7),
    (re.compile(r'(?:este|this)\s+(?:mês|month)', re.I), 30),
    (re.compile(r'(?:esta|this)\s+(?:quinzena|fortnight)', re.I), 15),
]

_TIME_MULTIPLIERS = {
    'dia': 1, 'dias': 1, 'day': 1, 'days': 1,
    'semana': 7, 'semanas': 7, 'week': 7, 'weeks': 7,
    'mês': 30, 'meses': 30, 'month': 30, 'months': 30,
    'ano': 365, 'anos': 365, 'year': 365, 'years': 365,
}


def _extract_time_constraint(text: str) -> Optional[int]:
    """
    Extrai restrição de tempo (max_days) de uma mensagem em linguagem natural.

    Retorna o número de dias ou None se não houver menção de tempo.

    Exemplos:
    - "notícias da última semana" → 7
    - "what happened in the last 3 days" → 3
    - "notícias de hoje" → 1
    - "what is AI?" → None
    """
    for pattern, multiplier in _TIME_PATTERNS:
        m = pattern.search(text)
        if m:
            try:
                n = int(m.group(1))
            except (IndexError, ValueError):
                n = 1
            return n * multiplier

    return None


# ══════════════════════════════════════════════════════════════════════════════
# EXTRAÇÃO DE TÓPICO
# ══════════════════════════════════════════════════════════════════════════════

_QUESTION_PREFIXES = re.compile(
    r'^(?:'
    r'what(?:\s+(?:is|are|was|were|about|does|do|did|has|have|had|happened|is\s+going\s+on|is\s+happening))?'
    r"|what's"
    r'|tell\s+me\s+(?:about|the\s+latest)'
    r'|qu(?:em|al|ais)'
    r'|o\s+que(?:\s+(?:é|ea|são|está|estão|foi|foram|há|tem|ta|tá))?'
    r'|como(?:\s+(?:está|estão|era|foi|funciona))?'
    r'|onde(?:\s+(?:é|está|estão|fica))?'
    r'|quando(?:\s+(?:é|foi|será|aconteceu))?'
    r'|por\s+quê?'
    r'|notícias?(?:\s+(?:sobre|de|do|da))?'
    r'|show\s+me'
    r'|explain'
    r'|describe'
    r'|give\s+me'
    r'|inform(?:e|ation)'
    r')\s+',
    re.I,
)

_TIME_SUFFIXES = re.compile(
    r'\s+'
    r'(?:'
    r'(?:nest|últim|this|last|past)\s+\w+'
    r'|(?:hoje|ontem|today|yesterday|agora|now)'
    r'|(?:\d+\s+(?:dia|semana|mês|ano|day|week|month|year)s?)'
    r')\s*$',
    re.I,
)


def _extract_topic(text: str) -> str:
    """
    Extrai o tópico principal de uma pergunta, removendo prefixes
    interrogativos e sufixos temporais.

    Exemplos:
    - "What is happening in Ukraine?" → "Ukraine"
    - "O que está acontecendo na Ucrânia?" → "Ucrânia"
    - "Notícias sobre eleições nos últimos 7 dias" → "eleições"
    - "Tell me about climate change" → "climate change"
    """
    topic = _QUESTION_PREFIXES.sub('', text).strip()
    topic = _TIME_SUFFIXES.sub('', topic).strip()

    topic = re.sub(r'[?!.]+$', '', topic)
    topic = re.sub(r'^(?:sobre|about|on)\s+', '', topic, flags=re.I)

    if len(topic) < 3:
        return text.strip()

    return topic


# ══════════════════════════════════════════════════════════════════════════════
# GERAÇÃO DE BUSCAS FALLBACK
# ══════════════════════════════════════════════════════════════════════════════

def _generate_fallback_searches(user_message: str) -> list[dict]:
    """
    Gera buscas fallback quando o LLM não chamou a ferramenta.

    Estratégia:
    1. Extrai tópico da mensagem
    2. Verifica recência implícita
    3. Extrai restrição temporal explícita
    4. Gera 1-2 buscas com os parâmetros encontrados
    """
    topic = _extract_topic(user_message)
    max_days = _extract_time_constraint(user_message)

    if _has_implicit_recency(user_message) and max_days is None:
        max_days = IMPLICIT_RECENCY_MAX_DAYS
        logger.info(
            f"[FALLBACK] Recência implícita detectada → max_days={max_days}"
        )

    searches: list[dict] = []

    search: dict = {"query": topic}
    if max_days is not None:
        search["max_days"] = max_days

    searches.append(search)

    if len(topic.split()) > 2:
        shorter = " ".join(topic.split()[:2])
        fallback: dict = {"query": shorter}
        if max_days is not None:
            fallback["max_days"] = max_days
        searches.append(fallback)

    logger.info(f"[FALLBACK] Buscas geradas: {searches}")
    return searches
