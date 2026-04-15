"""Redis-backed job store for recommendation lifecycle tracking."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis, from_url

from app.config import settings

logger = logging.getLogger(__name__)

JOB_KEY_PREFIX = "recommendation_job"
JOB_TTL_SECONDS = 60 * 60
JOB_TIMEOUT_SECONDS = 60 * 3

_redis_client: Redis | None = None


def _job_key(job_id: str) -> str:
    return f"{JOB_KEY_PREFIX}:{job_id}"


async def _get_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = from_url(settings.redis_url, encoding="utf-8", decode_responses=True)

    try:
        await _redis_client.ping()
    except Exception as exc:
        raise RuntimeError(f"Redis unavailable: {exc}") from exc

    return _redis_client


async def create_job(*, job_id: str, user_id: int, status: str, query: str | None = None) -> None:
    client = await _get_client()
    now = datetime.now(UTC).isoformat()
    payload = {
        "job_id": job_id,
        "user_id": str(user_id),
        "status": status,
        "query": query or "",
        "results": "[]",
        "error": "",
        "message": "",
        "celery_task_id": "",
        "created_at": now,
        "updated_at": now,
        "generated_at": "",
    }
    await client.hset(_job_key(job_id), mapping=payload)
    await client.expire(_job_key(job_id), JOB_TTL_SECONDS)


async def get_job(job_id: str) -> dict[str, Any] | None:
    client = await _get_client()
    raw = await client.hgetall(_job_key(job_id))
    if not raw:
        return None

    results = []
    if raw.get("results"):
        try:
            parsed = json.loads(raw["results"])
            if isinstance(parsed, list):
                results = parsed
        except json.JSONDecodeError:
            logger.warning("Invalid results JSON for job_id=%s", job_id)

    return {
        "job_id": raw.get("job_id", job_id),
        "user_id": int(raw.get("user_id") or 0),
        "status": raw.get("status", "processing"),
        "query": raw.get("query") or None,
        "results": results,
        "error": raw.get("error") or None,
        "message": raw.get("message") or "",
        "celery_task_id": raw.get("celery_task_id") or None,
        "created_at": raw.get("created_at") or None,
        "updated_at": raw.get("updated_at") or None,
        "generated_at": raw.get("generated_at") or None,
    }


async def update_job(job_id: str, **updates: Any) -> None:
    client = await _get_client()

    serialized: dict[str, str] = {}
    for key, value in updates.items():
        if key == "results":
            serialized[key] = json.dumps(value or [], ensure_ascii=False)
        elif value is None:
            serialized[key] = ""
        else:
            serialized[key] = str(value)

    serialized["updated_at"] = datetime.now(UTC).isoformat()

    await client.hset(_job_key(job_id), mapping=serialized)
    await client.expire(_job_key(job_id), JOB_TTL_SECONDS)


def is_job_timed_out(created_at: str | None) -> bool:
    if not created_at:
        return False
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    elapsed = (datetime.now(UTC) - created).total_seconds()
    return elapsed > JOB_TIMEOUT_SECONDS
