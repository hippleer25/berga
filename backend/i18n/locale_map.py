"""
locale_map — maps normalised locale codes to DuckDuckGo region strings
and Accept-Language header values.

Used by search_item_online.py, search_feed_online.py, post/load.py,
and search_feed_urls.py.
"""

from __future__ import annotations

DDG_REGION: dict[str, str] = {
    "pt": "wt-br",
    "en": "us-en",
    "es": "es-es",
    "de": "de-de",
    "fr": "fr-fr",
}

ACCEPT_LANGUAGE: dict[str, str] = {
    "pt": "pt-BR,pt;q=0.9,en;q=0.8",
    "en": "en-US,en;q=0.9",
    "es": "es-ES,es;q=0.9,en;q=0.8",
    "de": "de-DE,de;q=0.9,en;q=0.8",
    "fr": "fr-FR,fr;q=0.9,en;q=0.8",
}


def ddg_region(locale: str | None = None) -> str:
    from i18n import get_locale, DEFAULT_LOCALE
    loc = locale or get_locale()
    return DDG_REGION.get(loc, DDG_REGION[DEFAULT_LOCALE])


def accept_language_header(locale: str | None = None) -> str:
    from i18n import get_locale, DEFAULT_LOCALE
    loc = locale or get_locale()
    return ACCEPT_LANGUAGE.get(loc, ACCEPT_LANGUAGE[DEFAULT_LOCALE])
