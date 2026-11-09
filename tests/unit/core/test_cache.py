"""Unit tests for the Redis-backed referential cache."""

from __future__ import annotations

from fakeredis.aioredis import FakeRedis

from letmegetin.core.cache import NullCache, RedisCache


async def test_redis_cache_roundtrip() -> None:
    cache = RedisCache(FakeRedis(decode_responses=True))

    assert await cache.get_json("missing") is None
    await cache.set_json("ref:1:categories", [{"slug": "hotel"}], ttl=30)

    assert await cache.get_json("ref:1:categories") == [{"slug": "hotel"}]


async def test_null_cache_never_hits() -> None:
    cache = NullCache()

    await cache.set_json("key", {"value": 1})

    assert await cache.get_json("key") is None
