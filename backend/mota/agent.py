"""
mota/agent.py — Bounded agent loop for the Mota chat engine.

Flow (per turn, replacing the old single-shot tool pipeline):

  1. Router plan (from chat_router) is embedded in the planning prompt.
  2. Loop up to AGENT_MAX_ROUNDS: the ROUTING LLM decides tool calls, we
     execute them and feed results back. When it stops calling tools (or the
     token budget is spent) → evidence collection ends.
  3. Empty-result retry: if the first round produced nothing, one extra
     loop round hints the model to try the alternate vertical (news ↔ web).
  4. Synthesis: the SYNTHESIS tier streams the final answer, citing sources
     by number ([1], [2]). URLs are never in the synthesis prompt — they
     live in the SourceRegistry and get streamed to the client as a final
     `sources` SSE event.
"""

from __future__ import annotations

import json
import logging
from typing import Iterator, Optional

from mota.ai_lib import call_llm_messages_with_tools, stream_llm_deltas
from mota.chat_config import (
    AGENT_MAX_ROUNDS,
    ENABLE_SELF_CHECK,
    AGENT_TOOL_CONTEXT_TOKEN_BUDGET,
    ENABLE_WIKI,
    SYNTHESIS_MAX_CONTINUATIONS,
    SYNTHESIS_OUTPUT_TOKENS,
    SYNTHESIS_BRIEF_OUTPUT_TOKENS,
)
from mota.chat_sse import _Status, _Sources, _Queries, _Thinking
from mota.ai_lib import generate_text
from mota.chat_tool_parser import (
    _parse_tool_arguments,
    _serialize_assistant_message,
    _try_parse_dsml_tool_calls,
)
from mota.chat_search import run_searches, _truncate_content, _strip_html
from mota.sources import SourceRegistry
from mota.tokens import count_tokens
from intelligence.cluster import load_events_from_db
from intelligence.similar import get_similar_articles
from i18n.prompts import get_prompt
from search.item.search_item_online import extract_text_from_url

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════

TOPIC_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "topic_search",
        "description": (
            "Busca notícias recentes (feeds + web) usando NLP semântico para um ângulo "
            "do tema. Cada chamada executa UMA busca; você pode chamar esta ferramenta "
            "diversas vezes. Após receber resultados, se forem insuficientes, chame "
            "novamente com outros termos ou vertical. Quando os resultados forem "
            "suficientes, encerre (chame nenhuma ferramenta) para permitir a resposta."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Palavras-chave descritivas em linguagem natural (no idioma do usuário).",
                },
                "vertical": {
                    "type": "string",
                    "enum": ["news", "web"],
                    "description": "news = notícias datadas; web = páginas gerais p/ contexto e definições.",
                },
                "min_days": {"type": "integer", "description": "Artigos publicados há pelo menos N dias."},
                "max_days": {"type": "integer", "description": "Artigos publicados há no máximo N dias."},
            },
            "required": ["query"],
        },
    },
}

GET_CURRENT_EVENTS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_current_events",
        "description": (
            "Retorna os principais eventos/notícias da semana, agrupados por clustering. "
            "Use para panoramas gerais ('o que está acontecendo') — mais barato que topic_search."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "enum": ["mine", "all"],
                    "description": "'mine' filtra para as inscrições do usuário, 'all' para global. Default: 'all'.",
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
            "Extrai o texto completo de um artigo específico pela URL. "
            "Use quando precisa do conteúdo integral de uma fonte já encontrada."
        ),
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
}

GET_SIMILAR_TOOL = {
    "type": "function",
    "function": {
        "name": "get_similar",
        "description": "Encontra artigos similares a um artigo conhecido (por item_id ou url_hash).",
        "parameters": {
            "type": "object",
            "properties": {"item_id": {"type": "string"}},
            "required": ["item_id"],
        },
    },
}

SEARCH_WIKI_TOOL = {
    "type": "function",
    "function": {
        "name": "search_wiki",
        "description": (
            "Resumo enciclopédico (Wikipedia) para perguntas de fundo "
            "('quem é X', 'como funciona Y'). Não use para atualidades."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Título do conceito/pessoa a consultar."},
            },
            "required": ["topic"],
        },
    },
}

ALL_TOOLS = [
    TOPIC_SEARCH_TOOL,
    GET_CURRENT_EVENTS_TOOL,
    READ_ARTICLE_TOOL,
    GET_SIMILAR_TOOL,
    SEARCH_WIKI_TOOL,
]


# ══════════════════════════════════════════════════════════════════════════════
# TOOL HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

def _handle_get_current_events(feed_filter: list[str] | None = None) -> tuple[str, list[dict]]:
    """Eventos da semana. Retorna (texto compacto, artigos-base do texto)."""
    events = load_events_from_db()
    if not events:
        return "Nenhum evento clusterizado encontrado para esta semana.", []

    if feed_filter:
        feed_set = set(feed_filter)
        filtered_events = []
        for event in events:
            kept = [a for a in event.get("articles", [])
                    if a.get("feed_sha256") in feed_set]
            if not kept:
                continue
            unique_feeds = len(set(a.get("feed_sha256") for a in kept if a.get("feed_sha256")))
            if len(kept) < 2 and unique_feeds < 1:
                continue
            filtered_event = dict(event)
            filtered_event["articles"] = kept
            filtered_event["article_count"] = len(kept)
            filtered_event["unique_feeds"] = unique_feeds
            filtered_events.append(filtered_event)
        events = filtered_events

    if not events:
        return "Nenhum evento clusterizado nas inscrições do usuário para esta semana.", []

    lines = ["Eventos da semana (ordenados por relevância):\n"]
    attach: list[dict] = []

    for i, event in enumerate(events[:12], 1):
        summary = event.get("summary", "Sem resumo")
        count = event.get("article_count", 0)
        feeds = event.get("unique_feeds", 0)
        articles = event.get("articles", [])

        top_sources = ", ".join(a.get("source", a.get("feed_title", "?")) for a in articles[:3])
        lines.append(f"[{i}] {summary} ({count} artigos, {feeds} fontes: {top_sources})")

        for a in articles[:2]:
            if a.get("title"):
                attach.append(dict(a))

    return "\n".join(lines), attach


def _handle_read_article(url: str) -> str:
    if not url:
        return "URL não fornecida."
    try:
        full_text = extract_text_from_url(url)
    except Exception as e:
        logger.error(f"[READ_ARTICLE] Erro ao extrair texto de {url}: {e}")
        return f"Erro ao ler artigo: {e}"
    if not full_text:
        return "Não foi possível extrair texto do artigo."
    return f"Conteúdo completo do artigo ({url}):\n{_truncate_content(full_text)}"


def _handle_get_similar(item_id: str) -> str:
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
# AGENT LOOP
# ══════════════════════════════════════════════════════════════════════════════

def _plan_context(plan: dict) -> str:
    return json.dumps(
        {
            "kind": plan.get("kind"),
            "standalone_query": plan.get("standalone_query"),
            "sources": plan.get("sources"),
            "time": plan.get("time"),
            "expect_brief": plan.get("expect_brief"),
        },
        ensure_ascii=False,
    )


def _evidence_self_check(plan, user_message, registry, usage_out=None, session_id=None) -> Optional[dict]:
    """
    One cheap ROUTING-tier check: does the collected evidence (registry
    titles) look sufficient to answer? On insufficiency returns a single
    gap-driven search query. Never raises. Skips silently on failure.
    """
    try:
        block = registry.prompt_block()
        if not block:
            return {"sufficient": False, "query": plan.get("standalone_query"), "vertical": "news"}
        payload = (
            f"Pergunta: {user_message}\n\n"
            f"Fontes coletadas até agora:\n{block}\n\n"
            "Responda APENAS com o JSON pedido."
        )
        raw = generate_text(
            prompt=payload,
            system_prompt=get_prompt("self_check"),
            usage="routing",
            max_tokens=160,
            temperature=0.0,
            session_id=session_id,
            usage_out=usage_out if usage_out is not None else {},
        )
        if not raw:
            return None
        # Parse (tolerating fences/minor malformation)
        text = raw.strip()
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            text = text[start:end + 1]
        import json as _json
        try:
            parsed = _json.loads(text)
        except _json.JSONDecodeError:
            from json_repair import repair_json
            try:
                parsed = _json.loads(repair_json(text))
            except Exception:
                return None
        if not isinstance(parsed, dict):
            return None
        sufficient = bool(parsed.get("sufficient"))
        gap = str(parsed.get("query") or "").strip()
        vertical = "web" if str(parsed.get("vertical", "news")).lower() == "web" else "news"
        logger.info(f"[AGENT] SELF_CHECK: sufficient={sufficient} gap={gap!r}")
        return {"sufficient": sufficient, "query": gap or None, "vertical": vertical}
    except Exception as e:
        logger.warning(f"[AGENT] SELF_CHECK falhou: {e}")
        return None


def _direct_plan_search(
    plan: dict,
    feed_filter: Optional[list[str]],
    source_mode: str,
    registry: SourceRegistry,
    collected_queries: Optional[list[str]] = None,
    publisher_affinity: Optional[dict] = None,
) -> tuple[str, list[dict]]:
    """Executa as sub_queries do plano em uma passada paralela + wiki opcional."""
    searches: list[dict] = []
    for sq in plan.get("sub_queries", []):
        if isinstance(sq, dict) and sq.get("query"):
            s = {"query": sq["query"]}
            if plan["time"].get("min_days"):
                s["min_days"] = plan["time"]["min_days"]
            if plan["time"].get("max_days"):
                s["max_days"] = plan["time"]["max_days"]
            searches.append(s)
    if not searches:
        searches = [{"query": plan["standalone_query"], "vertical": "news"}]

    text, arts = run_searches(
        searches,
        source_mode=source_mode,
        feed_filter=feed_filter,
        id_assigner=registry.add,
        publisher_affinity=publisher_affinity,
    )

    if ENABLE_WIKI and "wiki" in plan.get("sources", []):
        from mota import wiki as _wiki
        page = _wiki.fetch_background(plan["standalone_query"], plan.get("language", "en"))
        if page:
            text = f"[Wikipedia: {page['title']}]\n{page['extract']}\n\n{text}"

    if collected_queries is not None:
        collected_queries.extend(s.get("query", "") for s in searches if s.get("query"))
    return text, arts


def _parse_calls(message) -> tuple[list[tuple[str, dict, str]], list[dict]]:
    """
    Returns ((name, args, tool_call_id), ...) from structured tool calls, or
    ([], dsml_calls_as_dicts) if only DSML text calls are present.
    """
    tc = getattr(message, "tool_calls", None)
    calls: list[tuple[str, dict, str]] = []
    if tc:
        for tool_call in tc:
            name = tool_call.function.name
            args = _parse_tool_arguments(tool_call.function.arguments)
            calls.append((name, args, getattr(tool_call, "id", "")))
        return calls, []
    content = getattr(message, "content", "") or ""
    dsml = _try_parse_dsml_tool_calls(content)
    if dsml:
        return [], [{"name": n, "args": a} for n, a in dsml]
    return [], []


def run_agent(
    plan: dict,
    user_message: str,
    feed_filter: Optional[list[str]],
    source_mode: str,
    history: list[dict],
    registry: SourceRegistry,
    usage_out: Optional[dict] = None,
    publisher_affinity: Optional[dict] = None,
    session_id: str | None = None,
) -> Iterator:
    """
    Bounded agent loop.

    Yields _Status markers (planning/searching/reading/refining/synthesizing),
    raw answer chunks, one _Queries marker and one final _Sources marker.
    If `usage_out` is a dict, it is filled with approximate token usage
    counters for the turn (loop / evidence / answer).
    """
    evidence_blocks: list[str] = []
    got_articles = False
    tool_rounds_used = 0
    executed_queries: list[str] = []

    loop_messages: list[dict] = [
        {"role": "system", "content": get_prompt("agent")},
        *history,
        {
            "role": "user",
            "content": f"Plano do router: {_plan_context(plan)}\nPergunta do usuário: {user_message}",
        },
    ]

    def _budget() -> int:
        return count_tokens("\n\n".join(evidence_blocks))

    loop_usage_tokens = 0

    for round_idx in range(1, AGENT_MAX_ROUNDS + 1):
        yield _Status("planning" if round_idx == 1 else "refining")

        try:
            response = call_llm_messages_with_tools(
                loop_messages,
                ALL_TOOLS,
                tool_choice="auto",
                max_tokens=512,
                temperature=0.2,
                usage="routing",
                session_id=session_id,
            )
        except Exception as e:
            logger.error(f"[AGENT] Erro na chamada LLM: {e}", exc_info=True)
            break

        if response is None:
            break
        try:
            message = response.choices[0].message
        except (IndexError, AttributeError) as e:
            logger.error(f"[AGENT] Resposta malformada: {e}")
            break

        # Provider-native reasoning → visible thinking stream
        _rc = getattr(message, "reasoning_content", None)
        if _rc:
            yield _Thinking(str(_rc))

        _u = getattr(response, "usage", None)
        if _u:
            loop_usage_tokens += int(getattr(_u, "total_tokens", 0) or 0)
            logger.info(
                f"[AGENT][USAGE] rodada {round_idx}: "
                f"prompt={getattr(_u, 'prompt_tokens', '?')} "
                f"completion={getattr(_u, 'completion_tokens', '?')}"
            )

        calls, dsml_calls = _parse_calls(message)

        # ── Routing model decided no more tools are needed ────────────────────
        if not calls and not dsml_calls:
            if round_idx == 1 and not got_articles:
                yield _Status("searching")
                text, arts = _direct_plan_search(
                    plan, feed_filter, source_mode, registry, executed_queries
                )
                if arts:
                    got_articles = True
                evidence_blocks.append(_truncate_content(text, 6000))
            break

        if calls:
            loop_messages.append(_serialize_assistant_message(message))

        used_tools = False
        tool_rounds_used += 1

        for name, args, tool_call_id in calls:
            if name == "topic_search" and isinstance(args, dict) and args.get("query"):
                executed_queries.append(str(args["query"]))
            text, arts = _dispatch_tool(
                name, args, plan, feed_filter, source_mode, registry, publisher_affinity
            )
            used_tools = True
            if arts:
                got_articles = True
            if text:
                evidence_blocks.append(text.strip())
            loop_messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": (text or "")[:1200] or "(no output)",
            })

            if _budget() >= AGENT_TOOL_CONTEXT_TOKEN_BUDGET:
                break

        # DSML-only path (models without native tool calling): execute inline
        for dsml in dsml_calls:
            if dsml["name"] == "topic_search" and isinstance(dsml["args"], dict) and dsml["args"].get("query"):
                executed_queries.append(str(dsml["args"]["query"]))
            text, arts = _dispatch_tool(
                dsml["name"], dsml["args"], plan, feed_filter, source_mode, registry, publisher_affinity
            )
            used_tools = True
            if arts:
                got_articles = True
            if text:
                evidence_blocks.append(text.strip())

        if _budget() >= AGENT_TOOL_CONTEXT_TOKEN_BUDGET:
            logger.info(f"[AGENT] Orçamento de contexto atingido após {round_idx} rodada(s)")
            break

        if not got_articles and used_tools and round_idx < AGENT_MAX_ROUNDS:
            loop_messages.append({
                "role": "system",
                "content": (
                    "A primeira rodada não trouxe resultados úteis. Reavalie: use vertical='web' "
                    "se 'news' falhou, reformule os termos, ou encerre sem chamadas se a pergunta "
                    "não exige busca."
                ),
            })

    # ── Garantia de evidência mínima (nunca responde no vácuo) ────────────────
    if not evidence_blocks:
        yield _Status("searching")
        text, arts = _direct_plan_search(plan, feed_filter, source_mode, registry, executed_queries, publisher_affinity)
        if arts:
            got_articles = True
        evidence_blocks.append(_truncate_content(text, 6000))

    # ── Self-check: claims vs evidência (1 busca extra no máximo) ─────────────
    if ENABLE_SELF_CHECK and not plan.get("expect_brief"):
        yield _Status("refining")
        verdict = _evidence_self_check(plan, user_message, registry, usage_out=usage_out, session_id=session_id)
        if verdict and not verdict.get("sufficient") and verdict.get("query"):
            gap_query = str(verdict["query"])
            logger.info(f"[AGENT] SELF_CHECK detectou lacuna → busca extra: {gap_query!r}")
            executed_queries.append(gap_query)
            text, arts = _dispatch_tool(
                "topic_search",
                {"query": gap_query, "vertical": verdict.get("vertical", "news")},
                plan, feed_filter, source_mode, registry, publisher_affinity,
            )
            if arts:
                got_articles = True
            if text:
                evidence_blocks.append(text.strip())

    # ── Transparência: queries efetivamente executadas nesta rodada ───────────
    seen_q: set[str] = set()
    deduped_queries = [q for q in executed_queries if q and not (q in seen_q or seen_q.add(q))]
    yield _Queries(deduped_queries)

    # ── Síntese final com citações numeradas ──────────────────────────────────
    yield _Status("synthesizing")

    evidence = "\n\n".join(b for b in evidence_blocks if b)
    registry_block = registry.prompt_block()

    system_prompt = get_prompt("synthesis")
    if registry_block:
        system_prompt = f"{system_prompt}\n\n{registry_block}"

    synthesis_msgs = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": f"Pergunta do usuário: {user_message}\n\nEvidência:\n{evidence}"},
    ]

    answer_text = ""
    output_budget = (
        SYNTHESIS_BRIEF_OUTPUT_TOKENS
        if plan.get("expect_brief")
        else SYNTHESIS_OUTPUT_TOKENS
    )
    for kind, text in stream_llm_deltas(
        synthesis_msgs,
        max_tokens=output_budget,
        usage="synthesis",
        auto_continue=SYNTHESIS_MAX_CONTINUATIONS,
        session_id=session_id,
    ):
        if kind == "thinking":
            yield _Thinking(text)
        elif text:
            answer_text += text
            yield text

    sources_payload = registry.sse_payload(answer_text)
    if sources_payload:
        yield _Sources(sources_payload)

    logger.info(
        f"[AGENT][USAGE] total: loop={loop_usage_tokens}t "
        f"evidence≈{_budget()}t answer≈{count_tokens(answer_text)}t "
        f"rounds={tool_rounds_used}"
    )

    if usage_out is not None:
        usage_out["loop"] = usage_out.get("loop", 0) + loop_usage_tokens
        usage_out["evidence"] = usage_out.get("evidence", 0) + _budget()
        usage_out["answer"] = usage_out.get("answer", 0) + count_tokens(answer_text)


def _dispatch_tool(
    name: str,
    args: dict,
    plan: dict,
    feed_filter: Optional[list[str]],
    source_mode: str,
    registry: SourceRegistry,
    publisher_affinity: Optional[dict] = None,
) -> tuple[str, list[dict]]:
    """Run a single tool call. Returns (tool_text_for_llm, attached_articles)."""
    name = (name or "").strip()

    if name == "topic_search":
        query = str(args.get("query", "")).strip()
        if not query:
            return "Falha: query vazia.", []
        searches = [{
            "query": query,
            "vertical": args.get("vertical", "news"),
            "min_days": args.get("min_days"),
            "max_days": args.get("max_days"),
        }]
        return run_searches(
            searches,
            source_mode=source_mode,
            feed_filter=feed_filter,
            id_assigner=registry.add,
            publisher_affinity=publisher_affinity,
        )

    if name == "get_current_events":
        scope = args.get("scope", "all")
        ff = feed_filter if scope == "mine" else None
        return _handle_get_current_events(feed_filter=ff)

    if name == "read_article":
        url = str(args.get("url", "")).strip()
        # Accept "[3]"-style references: resolve to the registered URL
        resolved = registry.resolve_reference(url)
        if resolved:
            url = resolved
        return (_handle_read_article(url), [])

    if name == "get_similar":
        return (_handle_get_similar(str(args.get("item_id", ""))), [])

    if name == "search_wiki":
        if not ENABLE_WIKI:
            return ("Wikipedia lookup desativado.", [])
        from mota import wiki as _wiki
        page = _wiki.fetch_background(str(args.get("topic", "")), plan.get("language", "en"))
        if not page:
            return ("Nenhuma página enciclopédica correspondente encontrada.", [])
        return (
            f"[Wikipedia: {page['title']}]\n{page['extract']}\n{page['url']}",
            [],
        )

    logger.warning(f"[AGENT] Tool desconhecida: {name!r}")
    return ("Unsupported tool.", [])
