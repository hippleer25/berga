"""
utils/regex_utils.py — Safe regex evaluation with ReDoS protection.

Python 3.12 does not support re.compile(timeout=); we rely on pattern
validation (length cap + compile check) and catch re.error at match time.
For true catastrophic-backtracking protection, the `regex` third-party
package would be needed. This module provides the best-effort approach
with the standard library.
"""

from __future__ import annotations

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

MAX_PATTERN_LENGTH = 512


def validate_regex_pattern(pattern: str) -> tuple[bool, Optional[str]]:
    if not pattern:
        return False, "Pattern cannot be empty"
    if len(pattern) > MAX_PATTERN_LENGTH:
        return False, f"Pattern exceeds {MAX_PATTERN_LENGTH} characters"
    try:
        re.compile(pattern)
    except re.error as e:
        return False, str(e)
    return True, None


def safe_regex_match(
    pattern: str,
    text: str,
    flags: int = 0,
) -> Optional[re.Match]:
    if not pattern or not text:
        return None
    try:
        compiled = re.compile(pattern, flags)
        return compiled.search(text)
    except re.error:
        logger.warning("Invalid regex pattern: %s", pattern[:64])
        return None
