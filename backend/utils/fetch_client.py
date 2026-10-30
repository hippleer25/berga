"""
utils/fetch_client.py
─────────────────────
Central HTTP fetch ladder for page content:

  1. requests (current behaviour, normal browser-looking headers)
  2. on error → curl_cffi with Chrome TLS/HTTP2 impersonation
     (defeats library-fingerprint bot detection at zero RAM/CPU cost)
  3. Jina Reader — strictly opt-in (JINA_READER_MODE):
       off      → never used (default)
       fallback → only when steps 1+2 fail
       always   → skip steps 1+2, go straight to Jina
     Optional JINA_API_KEY raises the keyless 20 RPM limit to 500 RPM.

Responses from steps 1/2 are API-compatible (response.text / .status_code /
.raise_for_status()), so callers don't need to know which client served them.
Callers that only need plain text can use fetch_text() which also handles the
Jina mode (markdown output skips local readability extraction).
"""

import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

try:  # optional at import time so the API can boot without the dep
    from curl_cffi import requests as curl_requests
    _CURL_IMPERSONATE = "chrome"
except Exception:  # pragma: no cover
    curl_requests = None
    _CURL_IMPERSONATE = None
    logger.warning("[fetch] curl_cffi unavailable — ladder degrades to requests only")

# ── Config (env, opt-in) ─────────────────────────────────────────────────────
JINA_READER_MODE = os.getenv("JINA_READER_MODE", "off").strip().lower()
JINA_API_KEY = os.getenv("JINA_API_KEY", "").strip()
JINA_TIMEOUT = float(os.getenv("JINA_TIMEOUT", "20"))
JINA_BASE = os.getenv("JINA_READER_BASE", "https://r.jina.ai")

# Cloudflare challenge markers — HTTP 200 with these bodies is a block page
_CHALLENGE_MARKERS = (
    "just a moment",
    "cf-browser-verification",
    "cf_chl_opt",
    "challenge-platform",
    "attention required",
)


class FetchResult:
    __slots__ = ("text", "status_code", "via")

    def __init__(self, text: str, status_code: int, via: str):
        self.text = text
        self.status_code = status_code
        self.via = via  # "requests" | "curl_cffi" | "jina"

    def __bool__(self) -> bool:
        return bool(self.text)


def _looks_blocked(status: int, body: str) -> bool:
    if status >= 400:
        return True
    if not body or len(body) < 200:
        return True
    low = body[:2000].lower()
    return any(marker in low for marker in _CHALLENGE_MARKERS)


def _jina_headers(return_format: str | None) -> dict:
    headers = {"Accept": "text/plain", "X-Return-Format": return_format} \
        if return_format else {"Accept": "text/plain"}
    if JINA_API_KEY:
        headers["Authorization"] = f"Bearer {JINA_API_KEY}"
    return headers


def fetch_via_jina(url: str, return_format: str | None = None) -> str:
    """
    Jina Reader: https://r.jina.ai/{url} → LLM-friendly markdown (or HTML with
    return_format="html"). Returns "" on any failure (silently, cacheable).
    """
    try:
        resp = requests.get(
            f"{JINA_BASE}/{url}",
            headers=_jina_headers(return_format),
            timeout=JINA_TIMEOUT,
        )
        if resp.status_code != 200 or not resp.text:
            logger.debug("[fetch:jina] %s → status %d", url[:80], resp.status_code)
            return ""
        return resp.text
    except requests.RequestException as e:
        logger.debug("[fetch:jina] %s → %s", url[:80], e)
        return ""


def fetch(
    url: str,
    headers: dict | None = None,
    timeout: float = 10,
    jina_format: str | None = None,
) -> FetchResult:
    """
    Main ladder: requests → curl_cffi → Jina (mode-dependent).
    `jina_format` is only forwarded to Jina (e.g. "html" for reader-mode
    callers); steps 1/2 always return the raw body either way.
    """
    # Always mode: straight to Jina
    if JINA_READER_MODE == "always":
        text = fetch_via_jina(url, return_format=jina_format)
        if text:
            return FetchResult(text, 200, "jina")

    # Step 1 — normal requests
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        if not _looks_blocked(resp.status_code, resp.text or ""):
            return FetchResult(resp.text, resp.status_code, "requests")
        last_err = f"status {resp.status_code}"
    except requests.RequestException as e:
        last_err = str(e)

    # Step 2 — curl_cffi Chrome impersonation
    if curl_requests is not None:
        try:
            with curl_requests.Session(impersonate=_CURL_IMPERSONATE) as session:
                resp = session.get(url, headers=headers, timeout=timeout)
                body = resp.text or ""
                if not _looks_blocked(resp.status_code, body):
                    logger.debug("[fetch] curl_cffi salvou %s (%s)", url[:80], last_err[:80])
                    return FetchResult(body, resp.status_code, "curl_cffi")
            last_err = f"{last_err} / curl_cffi status {resp.status_code}"
        except Exception as e:
            last_err = f"{last_err} / curl_cffi {e}"
            logger.debug("[fetch] curl_cffi falhou %s: %s", url[:80], e)

    # Step 3 — Jina fallback mode
    if JINA_READER_MODE == "fallback":
        text = fetch_via_jina(url, return_format=jina_format)
        if text:
            return FetchResult(text, 200, "jina")

    logger.debug("[fetch] todos os degraus falharam para %s (%s)", url[:80], last_err[:120])
    return FetchResult("", 0, "none")


def clean_ai_text(html: str) -> str:
    """Strip scripts/styles/tags — plain text for the AI (existing behaviour)."""
    clean = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<style[^>]*>.*?</style>", " ", clean, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", clean)
    return re.sub(r"\s+", " ", clean).strip()


def fetch_html(url: str, headers: dict | None = None, timeout: float = 15) -> tuple[str, str]:
    """
    Ladder for HTML consumers (reader mode): requests → curl_cffi → Jina with
    X-Return-Format: html (so the local readability pipeline still runs).
    Returns (html, via); ("", "none") when everything failed.
    """
    trial = fetch(url, headers=headers, timeout=timeout, jina_format="html")
    # A Jina-html body is valid HTML; requests/curl_cffi bodies likewise.
    if trial.text:
        return trial.text, trial.via
    return "", trial.via
