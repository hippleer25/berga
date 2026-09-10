"""
chat.py
───────
Handler principal do chat do Mota IA.

Fluxo v3 (router → agente → síntese):
1. Artigos diretos do feed → extração profunda + síntese com citações
2. Mensagem simples (gap funções/saudações, via regex) → resposta direta
3. Demais mensagens →
     a. LLM router (ROUTING tier): classificação + rewrite standalone +
        sub-queries + fontes-alvo + filtro temporal
     b. Bounded agent loop (mota/agent.py): até AGENT_MAX_ROUNDS rodadas
        de tool calling, orçamento de contexto em tokens
     c. Síntese com citações numeradas [n] + evento `sources` SSE
"""

import os
os.environ.setdefault('LITELLM_LOG', 'WARNING')

import logging
from typing import Iterator, Optional

from mota.ai_lib import stream_llm_response
from mota.chat_config import SYNTHESIS_OUTPUT_TOKENS
from mota.chat_sse import (
    _sse_event, _sse_status, _sse_error, _sse_done, _sse_sources, _sse_queries,
    _Status, _Sources, _Queries,
)
from mota.chat_classifier import is_simple_message
from mota.chat_search import (
    _strip_html,
    _truncate_content,
    _enrich_with_full_text,
    _apply_context_budget,
)
from mota.chat_router import route_message
from mota.agent import run_agent
from mota.sources import SourceRegistry
from mota import conversation
from intelligence.recommendations import _resolve_feed_filter

logger = logging.getLogger(__name__)

_CHAT_PUB_AFFINITY_WEIGHT = 0.08


def _get_publisher_affinity(user_id) -> Optional[dict]:
    """
    Publisher affinity map (feed_sha256 → {'likes': n, 'dislikes': n}) from
    the user's learned profile, for gentle local-result boosting in chat.
    Returns None when the user has no recorded publisher engagement.
    """
    if not user_id:
        return None
    try:
        from database.init_db import get_db
        import json as _json
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(
                    "SELECT publisher_likes, publisher_dislikes FROM user_vectors WHERE user_id = %s",
                    (user_id,),
                )
                row = cursor.fetchone()
            finally:
                cursor.close()
        if not row:
            return None
        likes = _json.loads(row.get("publisher_likes") or "{}")
        dislikes = _json.loads(row.get("publisher_dislikes") or "{}")
        if not likes and not dislikes:
            return None
        return {"likes": likes, "dislikes": dislikes}
    except Exception as e:
        logger.warning(f"[CHAT] Falha ao carregar publisher_affinity user={user_id}: {e}")
        return None


def _resolve_chat_feed_filter(
    user: dict, scope: str, folder_id: str | None = None, feed_sha256: str | None = None
) -> Optional[list[str]]:
    """Resolve o feed_filter para busca no chat.

    scope == "mine" → inscrições do usuário (lista de feed_sha256), filtradas
                      por folder_id/feed_sha256. Vazio se não houver inscrições.
    scope == "all"  → None (corpus global).
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


def _effective_source_mode(user_mode: str, plan_sources: list[str]) -> str:
    """
    Concilia a preferência do usuário com o plano do router.
    Modo explícito do usuário (local/online) prevalece; no modo "mixed" o
    plano decide (fontes só locais → local, só web/wiki → online, resto → mixed).
    """
    if user_mode in ("local", "online"):
        return user_mode
    if not plan_sources:
        return "mixed"
    if "web" not in plan_sources and "wiki" not in plan_sources:
        return "local"
    if "feeds" not in plan_sources:
        return "online"
    return "mixed"


# ══════════════════════════════════════════════════════════════════════════════
# MODOS DE RESPOSTA SIMPLES
# ══════════════════════════════════════════════════════════════════════════════

def _stream_general(user_message: str, history: list[dict]) -> Iterator:
    """Resposta direta do tier synthesis (sem busca)."""
    from i18n.prompts import get_prompt
    msgs = [
        {"role": "system", "content": get_prompt("general")},
        *history,
        {"role": "user", "content": user_message},
    ]
    for chunk in stream_llm_response(msgs, max_tokens=SYNTHESIS_OUTPUT_TOKENS, usage="synthesis"):
        yield chunk


# ══════════════════════════════════════════════════════════════════════════════
# HANDLER DE ARTIGOS DIRETOS DO FEED
# ══════════════════════════════════════════════════════════════════════════════

def _handle_direct_articles(
    user_message: str,
    articles: list[dict],
    history: list[dict] | None = None,
    registry: SourceRegistry | None = None,
) -> Iterator:
    """Processa artigos enviados diretamente pelo usuário (com citações)."""
    from i18n.prompts import get_prompt

    logger.info(f"[DIRECT] Processando {len(articles)} artigos diretos do feed")
    registry = registry or SourceRegistry()

    yield _Status("reading")

    enriched: list[dict] = []
    for raw_article in articles:
        art = dict(raw_article)

        if art.get("description"):
            art["description"] = _truncate_content(_strip_html(art["description"]))

        art = _enrich_with_full_text(art)
        registry.add(art)
        enriched.append(art)

        deep_tag = " [✓ deep]" if art.get("deep_read") else " [✗ sem extração]"
        logger.info(f" → {art.get('title', '')}{deep_tag}")

    enriched = _apply_context_budget(enriched)

    yield _Status("synthesizing")

    blocks = [
        "O usuário selecionou os seguintes artigos do seu feed pessoal. "
        "O texto completo de cada artigo foi extraído diretamente da fonte original. "
        "Leia cada um com atenção e produza uma síntese detalhada com citações [n]:\n"
    ]
    for article in enriched:
        idx = registry.id_by_url(article.get("link", "")) or 0
        deep = " [leitura profunda]" if article.get("deep_read") else ""
        title = article.get("title", "Sem título")
        pub_date = (article.get("pub_date") or "")[:10]
        feed_title = article.get("feed_title", "")
        blocks.append(
            f"[{idx}]{deep} {pub_date} — {title} ({feed_title})\n"
            f"{article.get('link', '')}\n{_strip_html(article.get('description', ''))}"
        )

    articles_context = "\n\n".join(blocks)

    registry_block = registry.prompt_block()
    system_prompt = get_prompt("direct_articles")
    if registry_block:
        system_prompt = f"{system_prompt}\n\n{registry_block}"

    messages = [
        {"role": "system", "content": system_prompt},
        *(history or []),
        {"role": "user", "content": f"{user_message}\n\n{articles_context}"},
    ]

    answer_text = ""
    for chunk in stream_llm_response(messages, max_tokens=SYNTHESIS_OUTPUT_TOKENS, usage="synthesis"):
        answer_text += chunk
        yield chunk

    sources_payload = registry.sse_payload(answer_text)
    if sources_payload:
        yield _Sources(sources_payload)

    logger.info(f"[DIRECT] ✓ Concluído")


# ══════════════════════════════════════════════════════════════════════════════
# HANDLER PRINCIPAL (RAW)
# ══════════════════════════════════════════════════════════════════════════════

def _generate_chat_stream(chat_request, user, history: list[dict] | None = None) -> Iterator:
    """Handler principal do chat (retorna chunks/marcadores sem formatação SSE)."""
    logger.info(f"\n{'#'*70}")
    logger.info(f"[CHAT] Usuário: {user.get('username', user)}")
    logger.info(f"[CHAT] Mensagem: {chat_request.message!r}")

    user_message = chat_request.message
    source_mode = getattr(chat_request, "source_mode", "mixed")
    scope = getattr(chat_request, "scope", "mine")
    folder_id = getattr(chat_request, "folder_id", None)
    feed_sha256 = getattr(chat_request, "feed_sha256", None)
    history = history or []

    feed_filter = _resolve_chat_feed_filter(user, scope, folder_id, feed_sha256)
    logger.info(f"[CHAT] Escopo: {scope} | folder={folder_id} | feed={feed_sha256} "
                f"| feed_filter: {len(feed_filter) if feed_filter else 'global'}")

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

    # ── CASO 2: Saudação/pureza trivial (regex; sem custo de LLM) ─────────────
    if is_simple_message(user_message):
        logger.info("[CHAT] → Mensagem simples: resposta direta")
        yield _Status("thinking")
        yield from _stream_general(user_message, history)
        return

    # ── CASO 3: Router LLM + agent loop ──────────────────────────────────────
    user_id = user.get("id") if isinstance(user, dict) else None
    digest = conversation.digest_for_router(user_id) if user_id else ""
    usage_out: dict = {}

    yield _Status("planning")
    plan = route_message(user_message, history_digest=digest, usage_out=usage_out)

    if plan["kind"] in ("greeting", "general_chat"):
        logger.info(f"[CHAT] → Router: {plan['kind']} → resposta direta")
        yield from _stream_general(user_message, history)
        if user_id:
            conversation.add_token_usage(user_id, usage_out)
        return

    registry = SourceRegistry(conversation.load_sources(user_id) if user_id else [])
    effective_mode = _effective_source_mode(source_mode, plan["sources"])
    publisher_affinity = _get_publisher_affinity(user_id) if (scope == "mine" and feed_filter) else None
    logger.info(f"[CHAT] Router: kind={plan['kind']} sources={plan['sources']} "
                f"sub_queries={[q['query'] for q in plan['sub_queries']]} mode={effective_mode} "
                f"pub_aff={bool(publisher_affinity)}")

    yield from run_agent(
        plan,
        user_message,
        feed_filter=feed_filter,
        source_mode=effective_mode,
        history=history,
        registry=registry,
        usage_out=usage_out,
        publisher_affinity=publisher_affinity,
    )

    if user_id:
        conversation.save_sources(user_id, registry.entries)
        total = conversation.add_token_usage(user_id, usage_out)
        logger.info(f"[CHAT][USAGE] turn total: {usage_out} → daily={total}")


# ══════════════════════════════════════════════════════════════════════════════
# FORMATAÇÃO SSE
# ══════════════════════════════════════════════════════════════════════════════

def receive(chat_request, user) -> Iterator[str]:
    """
    Handler principal do chat com formatação SSE.
    """
    user_id = user.get("id") if isinstance(user, dict) else None
    history = conversation.prepare_history(user_id) if user_id else []
    if history:
        logger.info(f"[CHAT] História preparada: {len(history)} mensagens para user={user_id}")

    assistant_chunks: list[str] = []
    sources_to_persist: Optional[list[dict]] = None

    try:
        for chunk in _generate_chat_stream(chat_request, user, history=history):
            if isinstance(chunk, _Status):
                yield _sse_status(chunk.phase)
            elif isinstance(chunk, _Queries):
                yield _sse_queries(chunk.queries)
            elif isinstance(chunk, _Sources):
                sources_to_persist = [e for e in chunk.entries if e.get("url")]
                yield _sse_sources(chunk.entries)
            else:
                event = _sse_event(chunk)
                if event:
                    yield event
                    assistant_chunks.append(chunk)
    except Exception as e:
        logger.error(f"[CHAT] ✗ Erro não tratado: {e}", exc_info=True)
        yield _sse_error(str(e))

    if user_id:
        user_message = chat_request.message
        conversation.save_turn(user_id, "user", user_message)
        if assistant_chunks:
            assistant_response = "".join(assistant_chunks)
            if assistant_response.strip():
                conversation.save_turn(
                    user_id, "assistant", assistant_response, sources=sources_to_persist
                )

    yield _sse_done()
