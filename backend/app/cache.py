import json
import logging
from typing import Any

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self, url: str):
        self._url = url
        self._redis: redis.Redis | None = None

    async def get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self._url, decode_responses=True)
        return self._redis

    async def get(self, key: str) -> Any | None:
        try:
            r = await self.get_redis()
            data = await r.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
        return None

    async def delete(self, key: str) -> None:
        try:
            r = await self.get_redis()
            await r.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

    async def set(self, key: str, value: Any, expire: int = 3600) -> None:
        try:
            r = await self.get_redis()
            await r.set(key, json.dumps(value), ex=expire)
        except Exception as e:
            logger.error(f"Redis set error: {e}")


cache = RedisCache(settings.redis_url)