"""Fixed-window rate limiting: Redis when configured, in-memory fallback otherwise."""

from __future__ import annotations

import time
from dataclasses import dataclass

from redis.exceptions import RedisError

from letmegetin.config import settings
from letmegetin.core.redis import get_redis

# INCR + EXPIRE must be atomic: a crash between them would leave a key without TTL.
_LUA = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""


@dataclass
class RateLimitResult:
    """Outcome of one counter increment."""

    allowed: bool
    limit: int
    remaining: int
    retry_after: int


class InMemoryLimiter:
    """Per-process fallback; not shared across workers."""

    def __init__(self) -> None:
        self._windows: dict[str, tuple[int, float]] = {}

    async def hit(self, key: str, limit: int, window: int) -> RateLimitResult:
        now = time.monotonic()
        count, reset_at = self._windows.get(key, (0, now + window))
        if now >= reset_at:
            count, reset_at = 0, now + window
        count += 1
        self._windows[key] = (count, reset_at)
        return RateLimitResult(
            allowed=count <= limit,
            limit=limit,
            remaining=max(0, limit - count),
            retry_after=max(1, int(reset_at - now)),
        )

    def reset(self) -> None:
        self._windows.clear()


_memory = InMemoryLimiter()


async def check_rate_limit(key: str, limit: int) -> RateLimitResult:
    """Increment the window for ``key`` and return the decision."""
    window = settings.rate_limit_window
    client = get_redis()
    if client is not None:
        try:
            current, ttl = await client.eval(_LUA, 1, f"ratelimit:{key}", window)
            count = int(current)
            return RateLimitResult(
                allowed=count <= limit,
                limit=limit,
                remaining=max(0, limit - count),
                retry_after=max(1, int(ttl)),
            )
        except RedisError:
            # Availability over strictness: a Redis outage must not take the API down.
            pass
    return await _memory.hit(key, limit, window)


def reset_memory_limits() -> None:
    """Clear the fallback windows (tests)."""
    _memory.reset()
