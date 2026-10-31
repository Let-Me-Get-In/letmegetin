"""Shared async Redis client (None when ``LETMEGETIN_REDIS_URL`` is unset)."""

from __future__ import annotations

from redis.asyncio import Redis

from letmegetin.config import settings

_client: Redis | None = None


def get_redis() -> Redis | None:
    """Return the process-wide client, or None when Redis is not configured."""
    global _client
    if not settings.redis_url:
        return None
    if _client is None:
        _client = Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def reset_redis() -> None:
    """Drop the client (tests changing the URL)."""
    global _client
    _client = None
