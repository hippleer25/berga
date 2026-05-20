"""
prompts.py — Loads Mota system prompts from YAML files, keyed by locale.

Each YAML file in i18n/prompts/ contains four top-level keys:
  tool_calling, synthesis, direct_articles, general

get_prompt(name, locale) returns the prompt string.
Falls back to English if the locale file is missing.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent / "prompts"

_VALID_PROMPT_NAMES = frozenset({
    "tool_calling",
    "synthesis",
    "direct_articles",
    "general",
})

_cache: dict[str, dict[str, str]] = {}


def _load_locale(locale: str) -> dict[str, str]:
    path = _PROMPTS_DIR / f"{locale}.yaml"
    if not path.exists():
        if locale != "en":
            logger.warning("No prompt file for locale=%s — falling back to en", locale)
            return _load_locale("en")
        raise RuntimeError("English prompt file missing — cannot continue")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise RuntimeError(f"Prompt file {path} did not parse as a dict")
    return {k: str(v).strip() for k, v in data.items() if k in _VALID_PROMPT_NAMES}


def get_prompt(name: str, locale: str | None = None) -> str:
    from i18n import get_locale, DEFAULT_LOCALE
    loc = locale or get_locale()
    if loc not in _cache:
        _cache[loc] = _load_locale(loc)
    prompts = _cache[loc]
    if name not in prompts:
        if loc != DEFAULT_LOCALE:
            fallback = _cache.get(DEFAULT_LOCALE) or _load_locale(DEFAULT_LOCALE)
            _cache[DEFAULT_LOCALE] = fallback
            return fallback.get(name, "")
        raise KeyError(f"Prompt {name!r} not found in locale {loc!r}")
    return prompts[name]


def reload(locale: str | None = None) -> None:
    if locale:
        _cache.pop(locale, None)
    else:
        _cache.clear()
