"""
version.py — Instance version reporting and upstream release check.

The installed version comes from the APP_VERSION env var (injected by
docker-compose; "dev" when unset). The "update available" signal compares
it against the latest GitHub release tag of the upstream repo.

The release lookup is best-effort and fail-open:
- Result is cached in a shared Redis key (6h TTL) so the GitHub API
  rate limit (60 req/h per IP) is a non-issue even on multi-user instances.
- Redis down, GitHub down or an unparsable version ("dev") all degrade to
  update_available=False — never raise.
"""

from __future__ import annotations

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

GITHUB_REPO = os.getenv("UPSTREAM_REPO", "hippleer25/berga")
RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"
LATEST_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

_CACHE_KEY = "berga:version_check"
_CACHE_TTL = 6 * 3600  # seconds

_REDIS_HOST = os.getenv("REDIS_HOST", "redis")
_REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
_REDIS_DB = int(os.getenv("REDIS_DB", "0"))

_VERSION_RE = re.compile(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?")


def get_version() -> str:
    """Installed instance version (APP_VERSION env var; 'dev' fallback)."""
    return (os.getenv("APP_VERSION", "dev").strip() or "dev")


def _parse_version(value) -> tuple | None:
    """Parse 'v0.8', '0.8.2' into a comparable int tuple; None if unparsable."""
    if not isinstance(value, str):
        return None
    m = _VERSION_RE.match(value.strip())
    if not m:
        return None
    return tuple(int(p) if p else 0 for p in m.groups())


def _get_client():
    import redis

    try:
        client = redis.Redis(
            host=_REDIS_HOST,
            port=_REDIS_PORT,
            db=_REDIS_DB,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
        client.ping()
        return client
    except Exception as e:
        logger.warning("Redis unavailable for version check: %s", e)
        return None


def _fetch_latest_release() -> tuple[str, str]:
    """Query the GitHub API for the latest release tag. Raises on failure."""
    import requests

    resp = requests.get(
        LATEST_API_URL,
        timeout=3,
        headers={
            "User-Agent": f"berga/{get_version()}",
            "Accept": "application/vnd.github+json",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    tag = data.get("tag_name") or data.get("name") or ""
    html_url = data.get("html_url") or RELEASES_URL
    if not tag:
        raise ValueError("release payload has no tag_name")
    return tag, html_url


def check_for_update() -> dict:
    """Best-effort update check. Never raises; fails open to no-update."""
    info = {
        "version": get_version(),
        "latest_version": None,
        "latest_url": RELEASES_URL,
        "update_available": False,
        "checked": False,
    }
    current = _parse_version(info["version"])
    if current is None:
        # "dev" or unparsable — nothing meaningful to compare against.
        return info

    client = _get_client()
    cached = None
    if client:
        try:
            raw = client.get(_CACHE_KEY)
            if raw:
                cached = json.loads(raw)
        except Exception as e:
            logger.warning("Failed to read version-check cache: %s", e)

    if cached and isinstance(cached, dict) and cached.get("latest_version"):
        info["latest_version"] = cached.get("latest_version")
        info["latest_url"] = cached.get("latest_url") or RELEASES_URL
        info["checked"] = True
    else:
        try:
            tag, url = _fetch_latest_release()
            info["latest_version"] = tag
            info["latest_url"] = url
            info["checked"] = True
            if client:
                try:
                    client.set(
                        _CACHE_KEY,
                        json.dumps({"latest_version": tag, "latest_url": url}),
                        ex=_CACHE_TTL,
                    )
                except Exception as e:
                    logger.warning("Failed to cache version check: %s", e)
        except Exception as e:
            logger.warning("Release check failed: %s", e)
            return info

    latest = _parse_version(info["latest_version"])
    if latest:
        info["update_available"] = latest > current
    return info
