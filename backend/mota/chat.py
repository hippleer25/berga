"""
chat.py
───────
Handler principal do chat do Mota IA.

Fluxo de execução:
1. Artigos diretos do feed → extração profunda + síntese
2. Mensagem simples → resposta direta (sem busca)
3. Mensagem que requer info → tool calling + FALLBACK de busca

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

import logging
from typing import Iterator

from mota.ai_lib import call_llm_with_tools, stream_llm_response
from mota.chat_config import IMPLICIT_RECENCY_MAX_DAYS
from mota.chat_sse import _sse_event, _sse_status, _sse_error, _sse_done, _Status
from mota.chat_classifier import is_simple_message
from mota.chat_tool_parser import (
    _try_parse_text_tool_call,
    _parse_tool_arguments,
    _serialize_assistant_message,
)
from mota.chat_search import (
    _strip_html,
    _truncate_content,
    _enrich_with_full_text,
    _format_article_for_llm,
    _apply_context_budget,
    run_searches,
)
from mota.chat_query_parser import (
    _has_implicit_recency,
    _generate_fallback_searches,
)
from i18n.prompts import get_prompt

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPTS
# ══════════════════════════════════════════════════════════════════════════════

def _TOOL_CALLING_SYSTEM_PROMPT() -> str:
    return get_prompt("tool_calling")


def _SYNTHESIS_SYSTEM_PROMPT() -> str:
    return get_prompt("synthesis")


def _DIRECT_ARTICLES_SYSTEM_PROMPT() -> str:
    return get_prompt("direct_articles")


def _GENERAL_SYSTEM_PROMPT() -> str:
    return get_prompt("general")


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
# HANDLER DE ARTIGOS DIRETOS DO FEED
# ══════════════════════════════════════════════════════════════════════════════

def _handle_direct_articles(
    user_message: str,
    articles: list[dict],
) -> Iterator:
    """Processes articles sent directly by the user."""
    logger.info(f"[DIRECT] Processando {len(articles)} artigos diretos do feed")

    yield _Status("reading")

    enriched: list[dict] = []
    for raw_article in articles:
        art = dict(raw_article)

        if art.get("description"):
            art["description"] = _truncate_content(_strip_html(art["description"]))

        art = _enrich_with_full_text(art)
        enriched.append(art)

        deep_tag = " [✓ deep]" if art.get("deep_read") else " [✗ sem extração]"
        desc_len = len(_strip_html(art.get("description", "")))
        logger.info(f" → {art.get('title', '')}{deep_tag} ({desc_len} chars)")

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
        {"role": "system", "content": _DIRECT_ARTICLES_SYSTEM_PROMPT()},
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
    """Runs direct search when LLM didn't call a tool."""
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
            {"role": "system", "content": _GENERAL_SYSTEM_PROMPT()},
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
        {"role": "system", "content": _SYNTHESIS_SYSTEM_PROMPT()},
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

    logger.info(f"[CHAT] Modo: {source_mode} | Deep: {deep_reading}")
    logger.info(f"{'#'*70}")

    # ── CASE 2: Simple message (no search) ─────────────────────────────────
    if is_simple_message(user_message):
        logger.info("[CHAT] → Mensagem simples: resposta direta")
        yield _Status("thinking")

        msgs = [
            {"role": "system", "content": _GENERAL_SYSTEM_PROMPT()},
            {"role": "user", "content": user_message},
        ]

        chunk_count = 0
        for chunk in stream_llm_response(msgs):
            chunk_count += 1
            yield chunk

        logger.info(f"[CHAT] ✓ Resposta simples: {chunk_count} chunks")
        return

    # ── CASE 3: Message requiring information ──────────────────────────────
    yield _Status("searching")

    # ── 3a. Tentativa de tool calling ────────────────────────────────────────
    tool_call_failed = False
    initial_response = None

    try:
        initial_response = call_llm_with_tools(
            user_message,
            [TOPIC_SEARCH_TOOL],
            system_prompt=_TOOL_CALLING_SYSTEM_PROMPT(),
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
                f"[CHAT] Resposta LLM: role={getattr(message, 'role', '?')} "
                f"tool_calls={has_tool_calls} content={content_preview}"
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
                        logger.info(f" {i}. {s}")

                    articles_text, all_articles = run_searches(
                        searches,
                        source_mode=source_mode,
                        deep_reading=deep_reading,
                    )

                    if all_articles:
                        yield _Status("synthesizing")

                        messages = [
                            {"role": "system", "content": _SYNTHESIS_SYSTEM_PROMPT()},
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
        reason = "call error" if tool_call_failed else "model didn't call"
        logger.info(f"[CHAT] → Fallback ({reason})")
        yield from _fallback_search_and_synthesize(user_message, source_mode, deep_reading)
        return

    # ── 3e. Process structured tool calls ──────────────────────────────────
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
                "content": "Unsupported tool.",
            })
            continue

        arguments = _parse_tool_arguments(tool_call.function.arguments)
        searches = arguments.get("searches", [])

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
            logger.info(f" {i}. {s}")

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
        {"role": "system", "content": _SYNTHESIS_SYSTEM_PROMPT()},
        {"role": "user", "content": user_message},
        _serialize_assistant_message(message),
        *tool_results,
    ]

    logger.info(
        f"[CHAT] Síntese final: {len(tool_results)} tool_results "
        f"{len(all_articles)} artigos {len(messages)} msgs"
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
