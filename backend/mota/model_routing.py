"""
mota/model_routing.py — Protocol-family routing for OpenAI-compatible
gateways that expose more than one API surface under the same base URL.

Background: the opencode go gateway (https://opencode.ai/zen/go/v1) serves
different models through different protocol families — OpenAI Chat
Completions (/v1/chat/completions), OpenAI Responses (/v1/responses) and
Anthropic Messages (/v1/messages) — under the *same* base URL. A model that
is valid in /v1/models may still fail with a generic 500 if the request is
sent through the wrong surface, so the model string handed to LiteLLM has
to carry the right provider routing.

This module is intentionally model-agnostic:

  1. Explicit env override  — OPENCODE_MODEL_PROTOCOLS="id1=chat,id2=responses"
  2. Built-in default table — known models seen on this gateway
  3. Learned at runtime     — the ladder in ai_lib caches what actually worked
  4. Fallback               — "chat" (the most common surface)
"""

import logging
import os
import threading

logger = logging.getLogger(__name__)

# Protocol family → LiteLLM model prefix that targets the surface
_LADDER: list[str] = ["chat", "responses", "anthropic"]

# Known examples on the gateway (prefix match, case-insensitive).
# These are hints only — runtime learning (see ai_lib ladder) takes precedence.
_BUILTIN = {
    "glm-5.3-flash": "chat",
    "muse-spark-1.3-contributor": "responses",
    "mimo-v2.5": "chat",
    "union-alpha": "anthropic",
}

# Some gateway-side providers enforce a MINIMUM output token budget for
# reasoning models (reasoning tokens count against max_output_tokens; too
# small a budget is rejected with "unable to complete request:
# max_output_tokens"). Values below are floors clamped up to on every call.
_BUILTIN_MIN_OUTPUT = {
    "muse-spark-1.3-contributor": 1024,
}

# Streaming capability hints (prefix match):
#   "genuine" — tokens arrive progressively from the first bytes
#   "burst"   — the provider buffers the full generation then plays it back
#               at once (slow first token; nothing progressive to show)
#   "pseudo"  — a stream request is answered with one empty delta; ai_lib
#               falls back to a single non-streaming call (everything lands
#               in one chunk at the end)
# Used purely for diagnostics (an early, explicit warning in the logs).
_BUILTIN_STREAM_STYLE = {
    "glm-5.3-flash": "genuine",
    "mimo-v2.5": "genuine",
    "deepseek-v4.1-flash": "genuine",
    "muse-spark-1.3-contributor": "burst",
    "union-alpha": "pseudo",
}

# Prefixes a caller might put in *_LLM_MODEL before "bare" model id.
_KNOWN_PREFIXES = (
    "openai/responses/",
    "openai/chat_completions/",
    "openai/",
    "anthropic/",
)

_LOCK = threading.Lock()
# ("learning" cache: gateway base + bare model -> protocol that worked)
_learned: dict[tuple[str, str], str] = {}
_env_overrides: dict[str, str] | None = None


def _load_env_overrides() -> dict[str, str]:
    """Parse OPENCODE_MODEL_PROTOCOLS='model-id=chat,muse=responses,...'."""
    global _env_overrides
    if _env_overrides is None:
        raw = os.getenv("OPENCODE_MODEL_PROTOCOLS", "").strip()
        table: dict[str, str] = {}
        if raw:
            for pair in raw.split(","):
                pair = pair.strip()
                if not pair or "=" not in pair:
                    continue
                mid, _, proto = pair.partition("=")
                proto = proto.strip().lower()
                if mid.strip() and proto in _LADDER:
                    table[mid.strip().lower()] = proto
                else:
                    logger.warning(f"[ROUTING] Ignoring invalid OPENCODE_MODEL_PROTOCOLS entry: {pair!r}")
        _env_overrides = table
    return _env_overrides


def is_opencode(api_base: str | None) -> bool:
    return bool(api_base) and "opencode" in api_base.lower()


def bare_model_name(model: str) -> str:
    """Strip any LiteLLM provider prefix previously applied to the model id."""
    lowered = model.lower()
    for prefix in _KNOWN_PREFIXES:
        if lowered.startswith(prefix):
            return model[len(prefix):]
    return model


def min_output_tokens(bare_model: str, api_base: str | None) -> int:
    """Per-model minimum output budget floor (0 = no floor).

    Order: env override (OPENCODE_MIN_OUTPUT_TOKENS='id=n,...') >
    built-in prefix table > 0.
    """
    raw = os.getenv("OPENCODE_MIN_OUTPUT_TOKENS", "").strip()
    if raw:
        for pair in raw.split(","):
            mid, _, val = pair.partition("=")
            if mid.strip().lower() == bare_model.lower():
                try:
                    return max(0, int(val.strip()))
                except ValueError:
                    logger.warning(f"[ROUTING] Invalid OPENCODE_MIN_OUTPUT_TOKENS value: {pair!r}")
    for mid, floor in _BUILTIN_MIN_OUTPUT.items():
        if bare_model.lower().startswith(mid.lower()):
            return floor
    return 0


def stream_style(bare_model: str, api_base: str | None) -> str | None:
    """Streaming-style hint for diagnostics ("genuine"|"burst"|"pseudo"|None).

    Order: env override (OPENCODE_STREAM_STYLE='id=burst,...') >
    built-in prefix table > None (unknown = assume genuine).
    """
    raw = os.getenv("OPENCODE_STREAM_STYLE", "").strip()
    if raw:
        for pair in raw.split(","):
            mid, _, style = pair.partition("=")
            style = style.strip().lower()
            if mid.strip().lower() == bare_model.lower() and style in ("genuine", "burst", "pseudo"):
                return style
    for mid, style in _BUILTIN_STREAM_STYLE.items():
        if bare_model.lower().startswith(mid.lower()):
            return style
    return None


def resolve(bare_model: str, api_base: str | None) -> str:
    """Best-known protocol family for a bare model id on the gateway.

    Order: runtime-learned (works today) > env override > built-in table >
    default "chat". Learned entries must win over everything else written
    by a human, otherwise a user overriding a working route would keep
    forcing a broken protocol on every call.
    """
    key = (api_base or "", bare_model.lower())
    with _LOCK:
        learned_ttl = _learned.get(key)
    if learned_ttl:
        return learned_ttl

    overrides = _load_env_overrides()
    hit = overrides.get(bare_model.lower())
    if hit:
        return hit

    for mid, proto in _BUILTIN.items():
        if bare_model.lower().startswith(mid.lower()):
            return proto
    return "chat"


def record(bare_model: str, api_base: str | None, protocol: str) -> None:
    """Cache the protocol that demonstrably worked (ai_lib fallback ladder)."""
    with _LOCK:
        _learned[(api_base or "", bare_model.lower())] = protocol


def next_in_ladder(protocol: str) -> str | None:
    try:
        i = _LADDER.index(protocol)
    except ValueError:
        return None
    return _LADDER[i + 1] if i + 1 < len(_LADDER) else None


def protocol_sequence(bare_model: str, api_base: str | None) -> list[str]:
    """[resolved, then rest of ladder] — used by ai_lib's fallback ladder."""
    first = resolve(bare_model, api_base)
    seq = [first] + [p for p in _LADDER if p != first]
    return seq


def litellm_target(
    bare_model: str, protocol: str, api_base: str | None
) -> tuple[str, str | None]:
    """Map (bare model, protocol family) → (litellm model string, api_base).

    - chat:       openai/<model>          (OpenAI client → {base}/chat/completions)
    - responses:  openai/responses/<model> (litellm bridges → {base}/responses)
    - anthropic:  anthropic/<model>        (litellm → {base}/v1/messages);
                  a trailing /v1 must be stripped first or the client
                  would double it.
    """
    if protocol == "responses":
        return f"openai/responses/{bare_model}", api_base
    if protocol == "anthropic":
        base = api_base.rstrip("/") if api_base else None
        if base and base.endswith("/v1"):
            base = base[: -len("/v1")]
        return f"anthropic/{bare_model}", base
    return f"openai/{bare_model}", api_base
