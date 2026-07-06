"""
mota/chat_config.py — Constants for the Mota chat engine.

Every magic number and distribution table that was previously inline
in chat.py lives here so other submodules can import without circular
dependencies.
"""

import os

CONTENT_CHAR_LIMIT = 6_000

TOTAL_CONTEXT_CHAR_LIMIT = 40_000

SEARCH_THRESHOLD = 0.6

MAX_DEEP_READ_ARTICLES = 3

RECENCY_HALF_LIFE_DAYS = 7.0
RECENCY_BOOST_WEIGHT = 0.4

IMPLICIT_RECENCY_MAX_DAYS = 30

# Output token budget for the final chat synthesis stream.
# Default 1024 (down from stream_llm_response's 2048 default) — news
# answers should be concise; raise if you need longer explanations.
SYNTHESIS_OUTPUT_TOKENS = int(os.getenv("SYNTHESIS_OUTPUT_TOKENS", "1024"))

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
