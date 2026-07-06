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
from typing import Iterator, Optional

from mota.ai_lib import call_llm_with_tools, stream_llm_response
from mota.chat_config import IMPLICIT_RECENCY_MAX_DAYS, SYNTHESIS_OUTPUT_TOKENS
from mota.chat_sse import _sse_event, _sse_status, _sse_error, _sse_done, _Status
from mota.chat_classifier import is_simple_message
from mota.chat_tool_parser import (
    _parse_tool_arguments,
    _serialize_assistant_message,
    _try_parse_dsml_tool_calls,
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
from intelligence.recommendations import _resolve_feed_filter
from mota import conversation
from intelligence.cluster import load_events_from_db
from intelligence.similar import get_similar_articles
from search.item.search_item_online import extract_text_from_url

logger = logging.getLogger(__name__)


def _resolve_chat_feed_filter(
    user: dict, scope: str, folder_id: str | None = None, feed_sha256: str | None = None
) -> Optional[list[str]]:
    """Resolve o feed_filter para busca no chat.

    scope == "mine" → retorna as inscrições do usuário (lista de feed_sha256),
                      filtradas por folder_id/feed_sha256 se fornecidos.
                      Vazio se o usuário não tiver inscrições (a busca local
                      retornará 0 resultados e cairá no online/mixed).
    scope == "all"  → retorna None (sem restrição, busca no corpus global).
    """
    try:
        user_id = user.get("id")
    except AttributeError:
        user_id = None
    if not user_id or scope != "mine":
        return None
    try:
        return _resolve_feed_filter(user_id, folder_id, feed_sha256)
    except Exception as e:
        logger.warning(f"[CHAT] Falha ao resolver feed_filter do user={user_id}: {e}")
        return None


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

GET_CURRENT_EVENTS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_current_events",
        "description": (
            "Retorna os principais eventos/notícias da semana atual, agrupados por clustering. "
            "Use quando o usuário perguntar 'o que está acontecendo', 'notícias de hoje', "
            "'principais eventos', ou quiser um panorama geral. "
            "Mais barato que topic_search — prefira esta ferramenta para panoramas gerais."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "enum": ["mine", "all"],
                    "description": "Escopo dos eventos: 'mine' filtra para as inscrições do usuário, 'all' mostra eventos globais. Default: 'all'.",
                },
            },
        },
    },
}

READ_ARTICLE_TOOL = {
    "type": "function",
    "function": {
        "name": "read_article",
        "description": (
            "Extrai o texto completo de um artigo específico pela sua URL. "
            "Use quando você já tem o link de um artigo (do topic_search ou get_current_events) "
            "e precisa do conteúdo completo para responder detalhadamente."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL do artigo a ser lido em profundidade.",
                },
            },
            "required": ["url"],
        },
    },
}

GET_SIMILAR_TOOL = {
    "type": "function",
    "function": {
        "name": "get_similar",
        "description": (
            "Encontra artigos similares a um artigo específico. "
            "Use quando o usuário pedir 'mais como este' ou 'artigos relacionados'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "UUID ou url_hash do artigo de referência.",
                },
            },
            "required": ["item_id"],
        },
    },
}

ALL_TOOLS = [TOPIC_SEARCH_TOOL, GET_CURRENT_EVENTS_TOOL, READ_ARTICLE_TOOL, GET_SIMILAR_TOOL]


# ══════════════════════════════════════════════════════════════════════════════
# TOOL HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

def _handle_get_current_events(feed_filter: list[str] | None = None) -> str:
    """Retorna eventos da semana em formato compacto para o LLM.

    Args:
        feed_filter: se fornecido, filtra eventos para incluir apenas artigos
                     cujo feed_sha256 está na lista. Eventos que ficam com
                     poucos artigos/fontes após o filtro são descartados.
    """
    events = load_events_from_db()
    if not events:
        return "Nenhum evento clusterizado encontrado para esta semana."

    # Filter by user subscriptions if requested
    if feed_filter:
        feed_set = set(feed_filter)
        filtered_events = []
        for event in events:
            articles = event.get("articles", [])
            kept = [a for a in articles if a.get("feed_sha256") in feed_set]
            if not kept:
                continue
            # Recalculate counts
            unique_feeds = len(set(a.get("feed_sha256") for a in kept if a.get("feed_sha256")))
            if len(kept) < 2 and unique_feeds < 1:
                continue  # drop events with too little coverage
            filtered_event = dict(event)
            filtered_event["articles"] = kept
            filtered_event["article_count"] = len(kept)
            filtered_event["unique_feeds"] = unique_feeds
            filtered_events.append(filtered_event)
        events = filtered_events
        logger.info(f"[EVENTS] Filtered to {len(events)} events for user subscriptions")

    if not events:
        return "Nenhum evento clusterizado encontrado nas suas inscrições para esta semana."

    lines = ["Eventos da semana (ordenados por relevância):\n"]
    for i, event in enumerate(events[:15], 1):
        summary = event.get("summary", "Sem resumo")
        count = event.get("article_count", 0)
        feeds = event.get("unique_feeds", 0)
        articles = event.get("articles", [])

        top_sources = ", ".join(
            a.get("source", a.get("feed_title", "?")) for a in articles[:3]
        )
        lines.append(f"[{i}] {summary} ({count} artigos, {feeds} fontes: {top_sources})")

        for a in articles[:2]:
            title = a.get("title", "")
            url = a.get("url", "")
            if title and url:
                lines.append(f"    - {title}\n      {url}")

    return "\n".join(lines)


def _handle_read_article(url: str) -> str:
    """Extrai texto completo de um artigo pela URL."""
    if not url:
        return "URL não fornecida."

    try:
        full_text = extract_text_from_url(url)
    except Exception as e:
        logger.error(f"[READ_ARTICLE] Erro ao extrair texto de {url}: {e}")
        return f"Erro ao ler artigo: {e}"

    if not full_text:
        return "Não foi possível extrair texto do artigo."

    truncated = _truncate_content(full_text)
    return f"Conteúdo completo do artigo:\n{url}\n\n{truncated}"


def _handle_get_similar(item_id: str) -> str:
    """Encontra artigos similares ao artigo de referência."""
    if not item_id:
        return "item_id não fornecido."

    try:
        similar = get_similar_articles(item_id, limit=5)
    except Exception as e:
        logger.error(f"[GET_SIMILAR] Erro: {e}")
        return f"Erro ao buscar artigos similares: {e}"

    if not similar:
        return "Nenhum artigo similar encontrado."

    lines = ["Artigos similares encontrados:\n"]
    for i, art in enumerate(similar, 1):
        title = art.get("title", "Sem título")
        link = art.get("url", art.get("link", ""))
        feed = art.get("feed_title", "")
        score = art.get("similarity_score", 0)
        pub = (art.get("pub_date") or "")[:10]
        desc = _strip_html(art.get("description", ""))[:200]
        lines.append(f"[{i}] {pub} — {title} ({feed}) [sim={score:.2f}]\n{link}\n{desc}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# HANDLER DE ARTIGOS DIRETOS DO FEED
# ══════════════════════════════════════════════════════════════════════════════

def _handle_direct_articles(
    user_message: str,
    articles: list[dict],
    history: list[dict] | None = None,
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
        *(history or []),
        {"role": "user", "content": f"{user_message}\n\n{articles_context}"},
    ]

    chunk_count = 0
    for chunk in stream_llm_response(messages, max_tokens=SYNTHESIS_OUTPUT_TOKENS, usage="synthesis"):
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
    feed_filter: Optional[list[str]] = None,
    history: list[dict] | None = None,
) -> Iterator:
    """Runs direct search when LLM didn't call a tool."""
    logger.info(f"[FALLBACK] Iniciando busca direta")

    searches = _generate_fallback_searches(user_message)
    yield _Status("searching")

    articles_text, all_articles = run_searches(
        searches,
        source_mode=source_mode,
        deep_reading=deep_reading,
        feed_filter=feed_filter,
    )

    if not all_articles:
        logger.warning("[FALLBACK] Nenhum artigo encontrado")
        yield _Status("thinking")

        msgs = [
            {"role": "system", "content": _GENERAL_SYSTEM_PROMPT()},
            *(history or []),
            {"role": "user", "content": user_message},
        ]

        chunk_count = 0
        for chunk in stream_llm_response(msgs, max_tokens=SYNTHESIS_OUTPUT_TOKENS, usage="synthesis"):
            chunk_count += 1
            yield chunk

        logger.info(f"[FALLBACK] ✓ Resposta geral: {chunk_count} chunks")
        return

    yield _Status("synthesizing")

    messages = [
        {"role": "system", "content": _SYNTHESIS_SYSTEM_PROMPT()},
        *(history or []),
        {"role": "user", "content": f"{user_message}\n\n{articles_text}"},
    ]

    chunk_count = 0
    for chunk in stream_llm_response(messages, max_tokens=SYNTHESIS_OUTPUT_TOKENS, usage="synthesis"):
        chunk_count += 1
        yield chunk

    logger.info(f"[FALLBACK] ✓ Síntese concluída: {chunk_count} chunks")


# ══════════════════════════════════════════════════════════════════════════════
# HANDLER PRINCIPAL (RAW)
# ══════════════════════════════════════════════════════════════════════════════

def _generate_chat_stream(chat_request, user, history: list[dict] | None = None) -> Iterator:
    """Handler principal do chat (retorna chunks sem formatação SSE)."""
    logger.info(f"\n{'#'*70}")
    logger.info(f"[CHAT] Usuário: {user.get('username', user)}")
    logger.info(f"[CHAT] Mensagem: {chat_request.message!r}")

    source_mode = getattr(chat_request, "source_mode", "local")
    deep_reading = getattr(chat_request, "deep_reading", False)
    scope = getattr(chat_request, "scope", "mine")
    folder_id = getattr(chat_request, "folder_id", None)
    feed_sha256 = getattr(chat_request, "feed_sha256", None)
    user_message = chat_request.message

    # Resolve o escopo das fontes: "mine" restringe às inscrições do usuário,
    # "all" busca no corpus global. folder_id/feed_sha256 refinam ainda mais.
    feed_filter = _resolve_chat_feed_filter(user, scope, folder_id, feed_sha256)
    logger.info(f"[CHAT] Escopo: {scope} | folder={folder_id} | feed={feed_sha256} | feed_filter: {len(feed_filter) if feed_filter else 'global'}")

    # ── CASO 1: Artigos diretos do feed ──────────────────────────────────────
    raw_articles = getattr(chat_request, "articles", None) or []
    direct_articles = [
        a.model_dump() if hasattr(a, "model_dump") else dict(a)
        for a in raw_articles
    ]

    if direct_articles:
        logger.info(f"[CHAT] Modo: artigos diretos ({len(direct_articles)} artigos)")
        yield from _handle_direct_articles(user_message, direct_articles, history=history)
        return

    logger.info(f"[CHAT] Modo: {source_mode} | Deep: {deep_reading}")
    logger.info(f"{'#'*70}")

    # ── CASE 2: Simple message (no search) ─────────────────────────────────
    if is_simple_message(user_message):
        logger.info("[CHAT] → Mensagem simples: resposta direta")
        yield _Status("thinking")

        msgs = [
            {"role": "system", "content": _GENERAL_SYSTEM_PROMPT()},
            *(history or []),
            {"role": "user", "content": user_message},
        ]

        chunk_count = 0
        for chunk in stream_llm_response(msgs, max_tokens=SYNTHESIS_OUTPUT_TOKENS, usage="synthesis"):
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
            ALL_TOOLS,
            system_prompt=_TOOL_CALLING_SYSTEM_PROMPT(),
            tool_choice="auto",
            max_tokens=1024,
            temperature=0.2,
            usage="routing",
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

    # ── 3c. Sem tool calls estruturados → tentar DSML text format ──────────────
    if not has_tool_calls and message is not None and not tool_call_failed:
        content = getattr(message, 'content', '') or ''
        dsml_calls = _try_parse_dsml_tool_calls(content)

        if dsml_calls:
            logger.info(f"[CHAT] ✓ {len(dsml_calls)} tool calls em formato DSML")
            # Process DSML tool calls directly
            all_articles: list[dict] = []
            tool_results: list[dict] = []
            has_content = False

            for dsml_name, dsml_args in dsml_calls:
                logger.info(f"[CHAT] DSML tool call: {dsml_name!r}")

                if dsml_name == "topic_search":
                    searches = dsml_args.get("searches", [])
                    if _has_implicit_recency(user_message):
                        for s in searches:
                            if "max_days" not in s:
                                s["max_days"] = IMPLICIT_RECENCY_MAX_DAYS

                    if not searches:
                        continue

                    articles_text, raw_arts = run_searches(
                        searches,
                        source_mode=source_mode,
                        deep_reading=deep_reading,
                        feed_filter=feed_filter,
                    )
                    all_articles.extend(raw_arts)
                    if articles_text:
                        has_content = True
                    tool_results.append({"role": "tool", "content": articles_text})

                elif dsml_name == "get_current_events":
                    event_scope = dsml_args.get("scope", "all")
                    events_feed_filter = feed_filter if event_scope == "mine" else None
                    events_text = _handle_get_current_events(feed_filter=events_feed_filter)
                    if events_text and "nenhum" not in events_text.lower()[:30]:
                        has_content = True
                    tool_results.append({"role": "tool", "content": events_text})

                elif dsml_name == "read_article":
                    url = dsml_args.get("url", "")
                    article_text = _handle_read_article(url)
                    if article_text and "erro" not in article_text.lower()[:20]:
                        has_content = True
                    tool_results.append({"role": "tool", "content": article_text})

                elif dsml_name == "get_similar":
                    item_id = dsml_args.get("item_id", "")
                    similar_text = _handle_get_similar(item_id)
                    if similar_text and "nenhum" not in similar_text.lower()[:30]:
                        has_content = True
                    tool_results.append({"role": "tool", "content": similar_text})

            if has_content:
                yield _Status("synthesizing")
                messages = [
                    {"role": "system", "content": _SYNTHESIS_SYSTEM_PROMPT()},
                    *(history or []),
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": content},
                    *tool_results,
                ]
                chunk_count = 0
                for chunk in stream_llm_response(messages, max_tokens=SYNTHESIS_OUTPUT_TOKENS, usage="synthesis"):
                    chunk_count += 1
                    yield chunk
                logger.info(f"[CHAT] ✓ DSML síntese: {chunk_count} chunks")
                return
            else:
                logger.warning("[CHAT] ✗ DSML tool calls sem conteúdo → fallback")

    # ── 3d. Sem tool calls → FALLBACK (noun-phrase extraction) ────────────────
    if not has_tool_calls:
        reason = "call error" if tool_call_failed else "model didn't call"
        logger.info(f"[CHAT] → Fallback ({reason})")
        yield from _fallback_search_and_synthesize(user_message, source_mode, deep_reading, feed_filter=feed_filter, history=history)
        return

    # ── 3e. Process structured tool calls ──────────────────────────────────
    logger.info(f"[CHAT] ✓ Tool calls estruturados: {len(message.tool_calls)}")

    all_articles: list[dict] = []
    tool_results: list[dict] = []
    has_content = False  # tracks whether any tool returned useful content

    for tc_idx, tool_call in enumerate(message.tool_calls):
        fn_name = tool_call.function.name
        logger.info(f"[CHAT] Tool call [{tc_idx}]: {fn_name!r}")

        # ── topic_search ──────────────────────────────────────────────────
        if fn_name == "topic_search":
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
                feed_filter=feed_filter,
            )

            all_articles.extend(raw_arts)
            if articles_text:
                has_content = True

            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": articles_text,
            })

        # ── get_current_events ────────────────────────────────────────────
        elif fn_name == "get_current_events":
            try:
                args = _parse_tool_arguments(tool_call.function.arguments)
            except Exception:
                args = {}
            event_scope = args.get("scope", "all") if isinstance(args, dict) else "all"
            events_feed_filter = feed_filter if event_scope == "mine" else None
            events_text = _handle_get_current_events(feed_filter=events_feed_filter)
            if events_text and "nenhum" not in events_text.lower()[:30]:
                has_content = True
            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": events_text,
            })

        # ── read_article ──────────────────────────────────────────────────
        elif fn_name == "read_article":
            try:
                args = _parse_tool_arguments(tool_call.function.arguments)
            except Exception:
                args = {}
            url = args.get("url", "") if isinstance(args, dict) else ""
            article_text = _handle_read_article(url)
            if article_text and "erro" not in article_text.lower()[:20]:
                has_content = True
            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": article_text,
            })

        # ── get_similar ───────────────────────────────────────────────────
        elif fn_name == "get_similar":
            try:
                args = _parse_tool_arguments(tool_call.function.arguments)
            except Exception:
                args = {}
            item_id = args.get("item_id", "") if isinstance(args, dict) else ""
            similar_text = _handle_get_similar(item_id)
            if similar_text and "nenhum" not in similar_text.lower()[:30]:
                has_content = True
            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": similar_text,
            })

        else:
            logger.warning(f"[CHAT] ✗ Tool desconhecida: {fn_name!r}")
            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": "Unsupported tool.",
            })

    # Sem conteúdo útil → fallback
    if not has_content and not all_articles:
        logger.warning("[CHAT] ✗ Nenhum conteúdo via tool calls → fallback")
        yield from _fallback_search_and_synthesize(user_message, source_mode, deep_reading, feed_filter=feed_filter, history=history)
        return

    # ── 3f. Síntese final ─────────────────────────────────────────────────────
    yield _Status("synthesizing")

    messages = [
        {"role": "system", "content": _SYNTHESIS_SYSTEM_PROMPT()},
        *(history or []),
        {"role": "user", "content": user_message},
        _serialize_assistant_message(message),
        *tool_results,
    ]

    logger.info(
        f"[CHAT] Síntese final: {len(tool_results)} tool_results "
        f"{len(all_articles)} artigos {len(messages)} msgs"
    )

    chunk_count = 0
    for chunk in stream_llm_response(messages, max_tokens=SYNTHESIS_OUTPUT_TOKENS, usage="synthesis"):
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
    user_id = user.get("id") if isinstance(user, dict) else None

    # Load conversation history for multi-turn context
    history = conversation.load_history(user_id) if user_id else []
    if history:
        logger.info(f"[CHAT] História carregada: {len(history)} turnos para user={user_id}")

    # Collect assistant response chunks to persist after streaming
    assistant_chunks: list[str] = []

    try:
        for chunk in _generate_chat_stream(chat_request, user, history=history):
            if isinstance(chunk, _Status):
                yield _sse_status(chunk.phase)
            else:
                event = _sse_event(chunk)
                if event:
                    yield event
                    assistant_chunks.append(chunk)
    except Exception as e:
        logger.error(f"[CHAT] ✗ Erro não tratado: {e}", exc_info=True)
        yield _sse_error(str(e))

    # Persist the conversation turn (user message + assistant response)
    if user_id:
        user_message = chat_request.message
        conversation.save_turn(user_id, "user", user_message)
        if assistant_chunks:
            assistant_response = "".join(assistant_chunks)
            if assistant_response.strip():
                conversation.save_turn(user_id, "assistant", assistant_response)

    yield _sse_done()
