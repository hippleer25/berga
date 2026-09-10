"""
mota/chat_router.py — LLM-powered intent router for the Mota chat engine.

Replaces the old keyword/regex heuristics (chat_classifier's
NEWS_INDICATOR_WORDS, chat_query_parser's fallback generation) with a single
cheap LLM call (ROUTING tier) that produces a structured search plan:

  {
    "kind": "greeting|general_chat|direct_articles|encyclopedia|
             news_lookup|current_events",
    "standalone_query": str,           # follow-up aware rewrite
    "sub_queries": [{"query": str, "vertical": "news"|"web"}],  # 1-3
    "sources": ["feeds"|"web"|"wiki"|"events"],
    "time": {"min_days": int|null, "max_days": int|null},
    "expect_brief": bool,
    "language": "pt"|"en"|...
  }

Everything downstream (agent loop, synthesis) consumes this plan:
the standalone_query is what gets embedded in prompts so follow-up
questions ("e a economia?") keep their context.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

try:
    from json_repair import repair_json
    HAS_JSON_REPAIR = True
except ImportError:
    HAS_JSON_REPAIR = False

from mota.ai_lib import generate_text
from mota.chat_config import MAX_SUB_QUERIES, ROUTER_MAX_TOKENS
from i18n.prompts import get_prompt

logger = logging.getLogger(__name__)

VALID_KINDS = {
    "greeting", "general_chat", "direct_articles",
    "encyclopedia", "news_lookup", "current_events",
}
VALID_SOURCES = {"feeds", "web", "wiki", "events"}
VALID_VERTICALS = {"news", "web"}

DEFAULT_LANGS = {"en", "pt", "es", "fr", "de"}


def _default_plan(message: str, reason: str) -> dict:
    """Conservative plan used when the router call fails or outputs garbage."""
    logger.info(f"[ROUTER] Default plan ({reason})")
    return {
        "kind": "news_lookup",
        "standalone_query": message,
        "sub_queries": [{"query": message, "vertical": "news"}],
        "sources": ["feeds", "web"],
        "time": {"min_days": None, "max_days": None},
        "expect_brief": False,
        "language": "pt",
    }


def _coerce_bool(v, default: bool) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "yes", "1", "sim")
    return default


def _coerce_days(v):
    if v in (None, "", "null"):
        return None
    try:
        n = int(v)
        return max(0, min(n, 3650))
    except (TypeError, ValueError):
        return None


def route_message(message: str, history_digest: str = "", usage_out: dict | None = None) -> dict:
    """
    Classify the message and produce a search plan. Never raises —
    returns a conservative default if the LLM or JSON fails.
    """
    locale = None
    try:
        from i18n import get_locale
        locale = get_locale()
    except Exception:
        pass

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d (%A)")

    prompt = get_prompt("router").replace("{today}", today)
    user_payload = ""
    if history_digest:
        user_payload += f"Recent conversation:\n{history_digest}\n\n"
    user_payload += f"User message: {message.strip()}"

    raw = None
    try:
        raw = generate_text(
            prompt=user_payload,
            system_prompt=prompt,
            usage="routing",
            max_tokens=ROUTER_MAX_TOKENS,
            temperature=0.0,
            usage_out=usage_out if usage_out is not None else {},
        )
    except Exception as e:
        logger.error(f"[ROUTER] LLM call failed: {e}", exc_info=True)

    if not raw:
        return _default_plan(message, "no LLM output")

    logger.info(f"[ROUTER][USAGE] raw output: {len(raw)} chars")

    plan = _parse_plan_json(raw)

    # ── Normalize / validate ──────────────────────────────────────────────────
    kind = str(plan.get("kind", "")).strip().lower()
    if kind not in VALID_KINDS:
        kind = "news_lookup"

    standalone = str(plan.get("standalone_query") or message.strip()).strip()
    if not standalone:
        standalone = message.strip()

    # ── Sub-queries: built from LLM output, fall back to standalone ──────────
    sub_queries = []
    for sq in plan.get("sub_queries", []) or []:
        if isinstance(sq, dict) and str(sq.get("query", "")).strip():
            vertical = str(sq.get("vertical", "news")).strip().lower()
            if vertical not in VALID_VERTICALS:
                vertical = "news"
            sub_queries.append({"query": str(sq["query"]).strip(), "vertical": vertical})
        elif isinstance(sq, str) and sq.strip():
            sub_queries.append({"query": sq.strip(), "vertical": "news"})
        if len(sub_queries) >= MAX_SUB_QUERIES:
            break
    if not sub_queries:
        sub_queries = [{"query": standalone, "vertical": "news"}]

    # ── Sources ───────────────────────────────────────────────────────────────
    raw_sources = plan.get("sources") or []
    if isinstance(raw_sources, str):
        raw_sources = [s.strip() for s in raw_sources.split(",")]
    sources = [s for s in (str(s).strip().lower() for s in raw_sources) if s in VALID_SOURCES]
    if not sources:
        # Sensible mapping from kind
        if kind == "current_events":
            sources = ["events", "feeds", "web"]
        elif kind == "encyclopedia":
            sources = ["wiki", "web"]
        else:
            sources = ["feeds", "web"]

    # ── Time constraints ──────────────────────────────────────────────────────
    time_raw = plan.get("time") if isinstance(plan.get("time"), dict) else {}
    time = {
        "min_days": _coerce_days(time_raw.get("min_days")),
        "max_days": _coerce_days(time_raw.get("max_days")),
    }
    if kind == "current_events" and time["max_days"] is None:
        time["max_days"] = 7

    language = str(plan.get("language", "")).strip().lower()[:5]
    if language and language.split("-")[0] not in DEFAULT_LANGS:
        language = "en"

    result = {
        "kind": kind,
        "standalone_query": standalone,
        "sub_queries": sub_queries,
        "sources": sources,
        "time": time,
        "expect_brief": _coerce_bool(plan.get("expect_brief"), False),
        "language": language,
    }
    logger.info(f"[ROUTER] Plan: kind={kind} sources={sources} time={time} "
                f"sub_queries={[q['query'] for q in sub_queries]}")

    # Keep locale var used (avoid lint noise) — router stays locale-aware via prompt
    _ = locale
    return result


def _parse_plan_json(raw: str) -> dict:
    """Parse router JSON, tolerating markdown fences and minor malformation."""
    text = raw.strip()

    # Strip ```json fences
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]

    # Grab the outermost JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        text = text[start:end + 1]

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    if HAS_JSON_REPAIR:
        try:
            parsed = json.loads(repair_json(text))
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    logger.warning(f"[ROUTER] Unparseable plan JSON: {raw[:200]}")
    return {}
