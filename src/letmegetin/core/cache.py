"""Read-through cache for the referential (Redis when configured, no-op otherwise)."""

from __future__ import annotations

import json
from typing import Any, Protocol

from redis.exceptions import RedisError

from letmegetin.config import settings
from letmegetin.core.redis import get_redis


class Cache(Protocol):
    async def get_json(self, key: str) -> Any | None: ...

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None: ...


class NullCache:
    """Used when Redis is not configured: every read goes to PostgreSQL."""

    async def get_json(self, key: str) -> Any | None:
        return None

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        return None


class RedisCache:
    def __init__(self, client: Any) -> None:
        self._client = client

    async def get_json(self, key: str) -> Any | None:
        try:
            raw = await self._client.get(key)
        except RedisError:
            return None
        return json.loads(raw) if raw else None

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        try:
            await self._client.set(key, json.dumps(value), ex=ttl or settings.cache_ttl)
        except RedisError:
            return None


_null = NullCache()


def get_cache() -> Cache:
    client = get_redis()
    return RedisCache(client) if client is not None else _null
