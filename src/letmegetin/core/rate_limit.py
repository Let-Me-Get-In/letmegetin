"""Sliding-window rate limiting: Redis when configured, in-memory fallback otherwise."""

from __future__ import annotations

import secrets
import time
from collections import deque
from dataclasses import dataclass

from redis.exceptions import RedisError

from letmegetin.config import settings
from letmegetin.core.redis import get_redis

# Sliding window: remove hits older than the window, count, add the current hit if under limit.
_LUA = """
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
local key = KEYS[1]
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
local added = 0
if count < limit then
  redis.call('ZADD', key, now, member)
  count = count + 1
  added = 1
end
redis.call('PEXPIRE', key, window * 1000)
return {count, added, window}
"""


@dataclass
class RateLimitResult:
    """Outcome of one counter increment."""

    allowed: bool
    limit: int
    remaining: int
    retry_after: int


class InMemoryLimiter:
    """Per-process fallback; the limit is divided by the worker count by the caller."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}

    async def hit(self, key: str, limit: int, window: int) -> RateLimitResult:
        now = time.monotonic()
        hits = self._hits.setdefault(key, deque())
        cutoff = now - window
        while hits and hits[0] <= cutoff:
            hits.popleft()
        allowed = len(hits) < limit
        if allowed:
            hits.append(now)
        remaining = max(0, limit - len(hits))
        retry_after = max(1, int(window - (now - hits[0]))) if hits else window
        return RateLimitResult(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            retry_after=retry_after,
        )

    def reset(self) -> None:
        self._hits.clear()


_memory = InMemoryLimiter()


async def check_rate_limit(key: str, limit: int) -> RateLimitResult:
    """Count one hit for ``key`` and return the decision."""
    window = settings.rate_limit_window
    client = get_redis()
    if client is not None:
        try:
            now = time.time()
            member = f"{time.time_ns()}-{secrets.token_hex(4)}"
            current, added, _ = await client.eval(
                _LUA, 1, f"ratelimit:{key}", now, window, limit, member
            )
            count = int(current)
            return RateLimitResult(
                allowed=bool(int(added)),
                limit=limit,
                remaining=max(0, limit - count),
                retry_after=window,
            )
        except RedisError:
            # Availability over strictness: a Redis outage must not take the API down.
            pass
    # Each worker has its own window, so divide the budget to keep the aggregate bounded.
    fallback_limit = max(1, limit // max(1, settings.worker_count))
    return await _memory.hit(key, fallback_limit, window)


def reset_memory_limits() -> None:
    """Clear the fallback windows (tests)."""
    _memory.reset()
