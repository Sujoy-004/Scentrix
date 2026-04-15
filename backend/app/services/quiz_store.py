"""Redis-backed store for adaptive quiz sessions."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from redis.asyncio import Redis, from_url

from app.config import settings

QUIZ_KEY_PREFIX = "adaptive_quiz_session"
QUIZ_TTL_SECONDS = 30 * 60

_redis_client: Redis | None = None


def _quiz_key(session_id: str) -> str:
    return f"{QUIZ_KEY_PREFIX}:{session_id}"


async def _get_client() -> Redis:
    global _redis_client
    client = _redis_client
    if client is None:
        client = from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        _redis_client = client

    try:
        await client.ping()
    except Exception as exc:
        raise RuntimeError(f"Redis unavailable: {exc}") from exc

    return client


def quiz_expiry_utc() -> datetime:
    return datetime.now(UTC) + timedelta(seconds=QUIZ_TTL_SECONDS)


async def create_quiz_session(*, session_id: str, payload: dict[str, Any]) -> None:
    client = await _get_client()
    await client.set(_quiz_key(session_id), json.dumps(payload, ensure_ascii=False))
    await client.expire(_quiz_key(session_id), QUIZ_TTL_SECONDS)


async def get_quiz_session(session_id: str) -> dict[str, Any] | None:
    client = await _get_client()
    raw = await client.get(_quiz_key(session_id))
    if not raw:
        return None

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    return parsed


async def save_quiz_session(*, session_id: str, payload: dict[str, Any]) -> None:
    client = await _get_client()
    await client.set(_quiz_key(session_id), json.dumps(payload, ensure_ascii=False))
    await client.expire(_quiz_key(session_id), QUIZ_TTL_SECONDS)
