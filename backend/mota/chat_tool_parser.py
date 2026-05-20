"""
mota/chat_tool_parser.py — Tool-call parsing for the Mota chat engine.

Handles three formats of tool calls:
1. Structured (OpenAI-style function_call objects)
2. Text-based ([TOOL_CALLS]topic_search{...})
3. Regex fallback extraction from malformed JSON

Also provides assistant-message serialization for multi-turn conversations.
"""

from __future__ import annotations

import ast
import json
import logging
import re
from typing import Optional

try:
    from json_repair import repair_json
    HAS_JSON_REPAIR = True
except ImportError:
    HAS_JSON_REPAIR = False

logger = logging.getLogger(__name__)


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


_RE_QUERY = re.compile(r"""(?:"query"|'query')\s*:\s*(?:"([^"]+)"|'([^']+)')""")
_RE_MAX_DAYS = re.compile(r"""(?:"max_days"|'max_days')\s*:\s*(\d+)""")
_RE_MIN_DAYS = re.compile(r"""(?:"min_days"|'min_days')\s*:\s*(\d+)""")


def _extract_searches_regex(text: str) -> list[dict]:
    """Extracts searches via regex (parsing fallback)."""
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
    """Serializes assistant message for conversation format."""
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
