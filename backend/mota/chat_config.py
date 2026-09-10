"""
mota/chat_config.py — Constants for the Mota chat engine.

Every magic number and distribution table that was previously inline
in chat.py lives here so other submodules can import without circular
dependencies.
"""

import os

CONTENT_CHAR_LIMIT = 6_000

SEARCH_THRESHOLD = 0.6

# ── Search ranking ───────────────────────────────────────────────────────────
# Recency boost applied to similarity scores after search:
# boosted = similarity + RECENCY_BOOST_WEIGHT × exp(−age_days / RECENCY_HALF_LIFE_DAYS)
RECENCY_HALF_LIFE_DAYS = 7.0
RECENCY_BOOST_WEIGHT = 0.4

# Output token budget for the final chat synthesis stream.
# Default 1024 (down from stream_llm_response's 2048 default) — news
# answers should be concise; raise if you need longer explanations.
SYNTHESIS_OUTPUT_TOKENS = int(os.getenv("SYNTHESIS_OUTPUT_TOKENS", "1024"))

# Output budget when the router classifies the answer as expected-brief
# ("expect_brief": true) — a couple of sentences.
SYNTHESIS_BRIEF_OUTPUT_TOKENS = int(os.getenv("SYNTHESIS_BRIEF_OUTPUT_TOKENS", "384"))

POSTS_PER_QUERY_LOCAL_ONLINE = {
    1: 6,
    2: 4,
    3: 2,
}

POSTS_PER_QUERY_MIXED = {
    1: 12,
    2: 8,
    3: 4,
}

# ── Agent loop ────────────────────────────────────────────────────────────────
# How many tool-decision rounds the bounded agent loop may run (1 = single shot).
AGENT_MAX_ROUNDS = int(os.getenv("AGENT_MAX_ROUNDS", "2"))

# Total token budget available for accumulated tool results (across all rounds).
# When exceeded the loop stops collecting evidence and moves to synthesis.
AGENT_TOOL_CONTEXT_TOKEN_BUDGET = int(os.getenv("AGENT_TOKEN_BUDGET", "6000"))

# Max output tokens for the routing/planning LLM (tool decisions are short).
ROUTER_MAX_TOKENS = int(os.getenv("ROUTER_MAX_TOKENS", "384"))

# Per-user daily soft cap on approximate chat token usage (0 = unlimited).
# Enforced in /api/chat before routing; approximate (LLM usage + estimates).
CHAT_DAILY_TOKEN_BUDGET = int(os.getenv("CHAT_DAILY_TOKEN_BUDGET", "250000"))

# ── Conversation history ─────────────────────────────────────────────────────
# Token budget for the conversation history block injected into prompts.
HISTORY_TOKEN_BUDGET = int(os.getenv("HISTORY_TOKEN_BUDGET", "1200"))

# Number of most-recent turns kept verbatim; older turns are summarized.
HISTORY_VERBATIM_TURNS = int(os.getenv("HISTORY_VERBATIM_TURNS", "3"))

# Max tokens per turn summary block (summarized older turns are folded into one).
SUMMARY_CACHE_TTL_SECONDS = 3600

# ── Feature switches ─────────────────────────────────────────────────────────
ENABLE_WEB_VERTICAL = bool(int(os.getenv("ENABLE_WEB_VERTICAL", "1")))
ENABLE_WIKI = bool(int(os.getenv("ENABLE_WIKI", "1")))

MAX_SUB_QUERIES = 3
WIKI_EXTRACT_CHARS = 800
WIKI_TIMEOUT = 6
