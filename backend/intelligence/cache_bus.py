"""
intelligence/cache_bus.py — Cross-process cache invalidation bus.

The ranking / interaction caches in intelligence.recommendations are
in-process (RAM) with generous TTLs. When one process invalidates a
user's cache (boost click, interaction, feed change), other processes —
the arq worker, extra API replicas — would keep serving stale entries
until their TTL expired. This module publishes those invalidations over
Redis pub/sub so every subscribed process drops its copy immediately.

Design notes:
- Fire-and-forget best-effort: any Redis failure is swallowed; the local
  cache drop already happened in the caller's process.
- The subscriber NEVER publishes — no echo loops.
- `DISABLE_CACHE_BUS=1` turns the whole thing off (single-process deploys
  that never care can save a thread and a connection).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time

logger = logging.getLogger(__name__)

CHANNEL_NAME = "berga:cache:invalidate"

_DISABLED = os.getenv("DISABLE_CACHE_BUS", "").strip().lower() in ("1", "true", "yes")

_client = None
_subscriber_client = None
_client_lock = threading.Lock()
_last_fail_ts = 0.0
_FAIL_COOLDOWN = 30.0  # seconds between reconnection attempts after a failure

_started = False
_start_lock = threading.Lock()


def _redis_base_kwargs() -> dict:
    return dict(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=0,
        socket_connect_timeout=2,
    )


def _get_redis():
    """Cached sync Redis client for publishing (None while unavailable)."""
    global _client, _last_fail_ts
    if _client is not None:
        return _client
    if _DISABLED:
        return None
    now = time.monotonic()
    if now - _last_fail_ts < _FAIL_COOLDOWN:
        return None
    try:
        import redis as _redis_mod

        client = _redis_mod.Redis(
            **_redis_base_kwargs(),
            socket_timeout=2,
        )
        client.ping()
        with _client_lock:
            _client = client
        return _client
    except Exception as e:
        _last_fail_ts = now
        logger.debug("[CACHE-BUS] Redis unavailable: %s", e)
        return None


def _get_subscriber_redis():
    """
    Dedicated client for the pub/sub listener: NO socket read timeout (a
    silent channel is normal, not an error) with periodic health-check
    pings so a dead connection is detected and reconnected.
    """
    global _subscriber_client
    if _subscriber_client is not None:
        return _subscriber_client
    if _DISABLED:
        return None
    try:
        import redis as _redis_mod

        client = _redis_mod.Redis(
            **_redis_base_kwargs(),
            health_check_interval=15,
        )
        client.ping()
        with _client_lock:
            _subscriber_client = client
        return _subscriber_client
    except Exception as e:
        logger.debug("[CACHE-BUS] Subscriber Redis unavailable: %s", e)
        return None


def publish_cache_invalidation(user_id: int | None) -> bool:
    """
    Broadcast a cache invalidation for one user (or everyone when None).
    Never raises; returns True when the message went out.
    """
    client = _get_redis()
    if client is None:
        return False
    try:
        client.publish(CHANNEL_NAME, json.dumps({"user_id": user_id}))
        return True
    except Exception as e:
        global _last_fail_ts
        _last_fail_ts = time.monotonic()
        logger.debug("[CACHE-BUS] Publish failed: %s", e)
        return False


def _handle_message(payload) -> None:
    """Apply an invalidation message to THIS process's local caches."""
    try:
        data = json.loads(payload)
        user_id = data.get("user_id")
        if user_id is not None:
            user_id = int(user_id)
    except (TypeError, ValueError):
        user_id = None

    from intelligence.recommendations import (
        invalidate_cache,
        invalidate_interaction_cache,
    )

    # broadcast=False: the subscriber must never re-publish (echo loop).
    invalidate_cache(user_id, broadcast=False)
    invalidate_interaction_cache(user_id)
    logger.debug("[CACHE-BUS] Applied invalidation user=%s", user_id)


def _listen_forever() -> None:
    """Subscriber loop with reconnection. Daemon thread, never publishes."""
    while True:
        client = _get_subscriber_redis()
        if client is None:
            time.sleep(_FAIL_COOLDOWN)
            continue
        try:
            pubsub = client.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(CHANNEL_NAME)
            logger.info("[CACHE-BUS] Subscriber listening (channel=%s)", CHANNEL_NAME)
            for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                _handle_message(message.get("data"))
        except Exception as e:
            logger.warning("[CACHE-BUS] Listener disconnected: %s — retrying", e)
            # The connection is suspect: force a fresh one on the next loop.
            with _client_lock:
                globals()["_subscriber_client"] = None
            time.sleep(_FAIL_COOLDOWN)


def start_cache_bus() -> None:
    """
    Start the single daemon subscriber thread for this process. Safe to
    call repeatedly; no-op when the bus is disabled.
    """
    global _started
    if _DISABLED or _started:
        return
    with _start_lock:
        if _started:
            return
        _started = True
        threading.Thread(target=_listen_forever, name="cache-bus", daemon=True).start()
