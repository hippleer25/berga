"""
mota/tokens.py — Token-counting helper for context budgeting.

Uses litellm.token_counter (provider-aware) so the budget is accurate
for whatever model the synthesis tier resolves to. Falls back to a
char-based heuristic (chars / 4) if tokenization fails.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Default token budget reserved for the article context block inside the
# synthesis prompt. The actual model context window is usually much larger,
# but we keep the *article* block bounded so the model has room for the
# system prompt, conversation history, and output.
DEFAULT_CONTEXT_TOKEN_BUDGET = int(os.getenv("SYNTHESIS_CONTEXT_TOKEN_BUDGET", "6000"))

# Minimum tokens to keep per article when truncating (so a low-ranked
# article still has a usable snippet rather than being stripped to nothing).
MIN_TOKENS_PER_ARTICLE = 100

_CHAR_FALLBACK_RATIO = 4  # ~4 chars per token as a rough proxy


def _resolve_model_name(usage: str = "synthesis") -> str | None:
    """Resolve the model name for a given usage tier (for token counting)."""
    prefix = usage.upper()
    model = os.getenv(f"{prefix}_LLM_MODEL")
    if model:
        return model
    # Fall back through the chain
    fallbacks = {"routing": "CHATBOT", "summarize": "CHATBOT", "synthesis": "CHATBOT"}
    fb = fallbacks.get(usage.upper())
    if fb:
        return os.getenv(f"{fb}_LLM_MODEL")
    return None


def count_tokens(text: str, model: str | None = None) -> int:
    """
    Count tokens in `text` using litellm.token_counter.

    Falls back to len(text) // 4 if tokenization is unavailable or fails.
    Never raises.
    """
    if not text:
        return 0

    if not model:
        model = _resolve_model_name()

    if model:
        try:
            import litellm
            return litellm.token_counter(model=model, text=text)
        except Exception as e:
            logger.debug(f"[TOKENS] litellm.token_counter failed for {model}: {e}; using char fallback")

    return max(1, len(text) // _CHAR_FALLBACK_RATIO)


def count_messages_tokens(messages: list[dict], model: str | None = None) -> int:
    """Count total tokens across a list of {role, content} messages."""
    if not model:
        model = _resolve_model_name()
    if model:
        try:
            import litellm
            return litellm.token_counter(model=model, messages=messages)
        except Exception as e:
            logger.debug(f"[TOKENS] litellm messages counter failed for {model}: {e}; using char fallback")
    total = 0
    for m in messages:
        total += count_tokens(str(m.get("content", "")), model)
        total += 4  # role + delimiters overhead
    return total
