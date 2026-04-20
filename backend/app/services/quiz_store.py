"""Quiz session store — Redis-backed with in-memory fallback.

If Redis is unavailable (not configured or unreachable), sessions are stored
in process memory for the lifetime of the server instance. Quiz still works;
sessions are ephemeral across restarts.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable
from datetime import UTC, datetime, timedelta
from typing import Any, cast

logger = logging.getLogger(__name__)

QUIZ_TTL_SECONDS = 30 * 60
QUIZ_KEY_PREFIX = "adaptive_quiz_session"

# ── In-memory fallback store ──────────────────────────────────────────────────
_memory_store: dict[str, dict[str, Any]] = {}

# ── Redis wiring (optional) ───────────────────────────────────────────────────
_redis_client = None
_redis_available: bool | None = None  # None = untested


def _quiz_key(session_id: str) -> str:
    return f"{QUIZ_KEY_PREFIX}:{session_id}"


async def _get_redis():
    """Return a live Redis client or None if Redis is unavailable."""
    global _redis_client, _redis_available

    if _redis_available is False:
        return None  # already determined unavailable, skip

    try:
        from redis.asyncio import from_url

        from app.config import settings

        if _redis_client is None:
            _redis_client = from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
                ssl_cert_reqs=None,  # Required for Upstash TLS (rediss://)
            )

        from collections.abc import Awaitable
        from typing import cast
        await cast(Awaitable[bool], _redis_client.ping())
        _redis_available = True
        return _redis_client

    except Exception as exc:
        if _redis_available is not False:
            logger.warning(f"[QuizStore] Redis unavailable — falling back to in-memory store: {exc}")
        _redis_available = False
        _redis_client = None
        return None


def quiz_expiry_utc() -> datetime:
    return datetime.now(UTC) + timedelta(seconds=QUIZ_TTL_SECONDS)


async def create_quiz_session(*, session_id: str, payload: dict[str, Any]) -> None:
    client = await _get_redis()
    if client is not None:
        key = _quiz_key(session_id)
        await cast(Awaitable[Any], client.set(key, json.dumps(payload, ensure_ascii=False)))
        await cast(Awaitable[Any], client.expire(key, QUIZ_TTL_SECONDS))
    else:
        _memory_store[session_id] = payload


async def get_quiz_session(session_id: str) -> dict[str, Any] | None:
    client = await _get_redis()
    if client is not None:
        raw = await cast(Awaitable[str | None], client.get(_quiz_key(session_id)))
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    else:
        return _memory_store.get(session_id)


async def save_quiz_session(*, session_id: str, payload: dict[str, Any]) -> None:
    client = await _get_redis()
    if client is not None:
        key = _quiz_key(session_id)
        await cast(Awaitable[Any], client.set(key, json.dumps(payload, ensure_ascii=False)))
        await cast(Awaitable[Any], client.expire(key, QUIZ_TTL_SECONDS))
    else:
        _memory_store[session_id] = payload

