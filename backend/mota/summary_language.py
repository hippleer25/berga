"""
summary_language.py — User preference for AI summary output language.

The preference lives in the frontend's localStorage and is sent per-request
by API calls (article resume). A copy for the background cluster worker is
synced into a global Redis key (last writer wins — fine for single-user
home-server deployments).

Valid values: "auto" or a supported i18n locale ("pt", "en", "es", "de", "fr").
"""

from __future__ import annotations

import logging
import os

from i18n import SUPPORTED_LOCALES

logger = logging.getLogger(__name__)

_REDIS_HOST = os.getenv("REDIS_HOST", "redis")
_REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
_REDIS_DB = int(os.getenv("REDIS_DB", "0"))

_SUMMARY_LANG_KEY = "mota:prefs:summary_language"

LANGUAGE_NAMES = {
    "pt": "Portuguese",
    "en": "English",
    "es": "Spanish",
    "de": "German",
    "fr": "French",
}


def normalize_language(value) -> str:
    """Coerce an arbitrary client value to 'auto' or a supported locale."""
    if not isinstance(value, str):
        return "auto"
    value = value.strip().lower()
    if value in SUPPORTED_LOCALES:
        return value
    return "auto"


def fixed_language(locale) -> str | None:
    """Return a supported locale when the value is a fixed language, else None."""
    return locale if locale in SUPPORTED_LOCALES else None


def language_instruction(locale: str) -> str:
    """Explicit instruction appended to the user message with the article."""
    return f"[Write the summary in {LANGUAGE_NAMES[locale]}.]"


def _get_client():
    import redis

    try:
        client = redis.Redis(
            host=_REDIS_HOST,
            port=_REDIS_PORT,
            db=_REDIS_DB,
            socket_connect_timeout=3,
            socket_timeout=3,
            decode_responses=True,
        )
        client.ping()
        return client
    except Exception as e:
        logger.warning("Redis unavailable for summary-language pref: %s", e)
        return None


def set_stored_language(value: str) -> bool:
    """Persist the worker-side copy of the preference. Best-effort."""
    normalized = normalize_language(value)
    try:
        client = _get_client()
        if not client:
            return False
        if normalized == "auto" or fixed_language(normalized) is None:
            client.delete(_SUMMARY_LANG_KEY)
        else:
            client.set(_SUMMARY_LANG_KEY, normalized)
        return True
    except Exception as e:
        logger.warning("Failed to store summary-language pref: %s", e)
        return False


def get_stored_language() -> str:
    """Read the worker-side copy. 'auto' on any failure (default behavior)."""
    try:
        client = _get_client()
        if not client:
            return "auto"
        raw = client.get(_SUMMARY_LANG_KEY)
        return normalize_language(raw)
    except Exception as e:
        logger.warning("Failed to read summary-language pref: %s", e)
        return "auto"
