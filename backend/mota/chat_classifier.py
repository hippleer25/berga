"""
mota/chat_classifier.py — Simple-message vs. information-query detection.

Determines whether a user message is small-talk / greetings (no search
needed) or an information query that should trigger the search pipeline.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


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
