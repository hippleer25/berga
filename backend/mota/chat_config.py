"""
mota/chat_config.py — Constants for the Mota chat engine.

Every magic number and distribution table that was previously inline
in chat.py lives here so other submodules can import without circular
dependencies.
"""

CONTENT_CHAR_LIMIT = 6_000

TOTAL_CONTEXT_CHAR_LIMIT = 40_000

SEARCH_THRESHOLD = 0.6

MAX_DEEP_READ_ARTICLES = 3

RECENCY_HALF_LIFE_DAYS = 7.0
RECENCY_BOOST_WEIGHT = 0.4

IMPLICIT_RECENCY_MAX_DAYS = 30

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
