"""
mota/chat_tool_parser.py — Tool-call argument parsing for the Mota chat engine.

Handles parsing of structured tool-call arguments (JSON with repair fallback).
Also provides assistant-message serialization for multi-turn conversations.
Includes a DSML text-format parser for models that don't support native
function calling (e.g. some DeepSeek models).
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


# ── DSML text-format parser ──────────────────────────────────────────────────
# Some models (e.g. DeepSeek) emit tool calls in a text format like:
#   <｜｜DSML｜｜tool_calls>
#   <｜｜DSML｜｜invoke name="topic_search">
#   <｜｜DSML｜｜parameter name="searches">[{"query": "..."}]</｜｜DSML｜｜parameter>
#   </｜｜DSML｜｜invoke>
#   </｜｜DSML｜｜tool_calls>
# This parser extracts them into a list of (name, arguments_dict) tuples.

_RE_DSML_INVOKE = re.compile(
    r'<｜｜DSML｜｜invoke\s+name="([^"]+)">(.*?)</｜｜DSML｜｜invoke>',
    re.DOTALL,
)
_RE_DSML_PARAM = re.compile(
    r'<｜｜DSML｜｜parameter\s+name="([^"]+)"[^>]*>(.*?)</｜｜DSML｜｜parameter>',
    re.DOTALL,
)


def _try_parse_dsml_tool_calls(content: str) -> list[tuple[str, dict]] | None:
    """
    Parse DSML-format tool calls from model text output.
    Returns a list of (tool_name, arguments_dict) or None if no DSML found.
    """
    if not content or "DSML" not in content:
        return None

    invokes = _RE_DSML_INVOKE.findall(content)
    if not invokes:
        return None

    results = []
    for tool_name, invoke_body in invokes:
        params = _RE_DSML_PARAM.findall(invoke_body)
        args: dict = {}
        for param_name, param_value in params:
            param_value = param_value.strip()
            # Try to parse as JSON first
            try:
                args[param_name] = json.loads(param_value)
            except json.JSONDecodeError:
                if HAS_JSON_REPAIR:
                    try:
                        args[param_name] = json.loads(repair_json(param_value))
                        continue
                    except Exception:
                        pass
                # Keep as string if not JSON
                args[param_name] = param_value

        results.append((tool_name, args))
        logger.info(f"[DSML] Parsed tool call: {tool_name} with args keys={list(args.keys())}")

    return results if results else None


def _parse_tool_arguments(raw: str) -> dict:
    """Parseia argumentos de tool call (JSON com fallback para json_repair)."""
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
            searches = []

        parsed["searches"] = searches

    if isinstance(parsed.get("searches"), list):
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
