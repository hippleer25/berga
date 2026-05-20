"""
i18n — locale resolution for the Berga backend.

Provides a per-request locale context via a Starlette middleware that
reads the Accept-Language header.  Downstream code calls get_locale()
to retrieve the normalised two-letter code (e.g. "pt", "en", "de").

If no Accept-Language header is present, falls back to DEFAULT_LOCALE.
Only locales in SUPPORTED_LOCALES are accepted; anything else is
silently mapped to the default.
"""

from __future__ import annotations

import re
from contextvars import ContextVar

SUPPORTED_LOCALES: frozenset[str] = frozenset({"pt", "en", "es", "de", "fr"})
DEFAULT_LOCALE: str = "en"

_current_locale: ContextVar[str] = ContextVar("locale", default=DEFAULT_LOCALE)


def set_locale(locale: str) -> None:
    normalised = (locale or "").strip().lower()[:2]
    _current_locale.set(normalised if normalised in SUPPORTED_LOCALES else DEFAULT_LOCALE)


def get_locale() -> str:
    return _current_locale.get(DEFAULT_LOCALE)


def parse_accept_language(header: str | None) -> str:
    if not header:
        return DEFAULT_LOCALE
    for part in header.split(","):
        code = part.split(";")[0].strip().split("-")[0].lower()
        if code in SUPPORTED_LOCALES:
            return code
    return DEFAULT_LOCALE
