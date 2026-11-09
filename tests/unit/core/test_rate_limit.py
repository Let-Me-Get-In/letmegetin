"""Unit tests for the fixed-window limiter."""

from __future__ import annotations

import pytest

from letmegetin.core.rate_limit import InMemoryLimiter


async def test_window_allows_then_denies(monkeypatch: pytest.MonkeyPatch) -> None:
    now = 0.0
    monkeypatch.setattr("letmegetin.core.rate_limit.time.monotonic", lambda: now)
    limiter = InMemoryLimiter()

    first = await limiter.hit("key", 2, 60)
    second = await limiter.hit("key", 2, 60)
    third = await limiter.hit("key", 2, 60)

    assert first.allowed and second.allowed
    assert not third.allowed
    assert (third.remaining, third.retry_after) == (0, 60)


async def test_window_resets(monkeypatch: pytest.MonkeyPatch) -> None:
    now = 0.0
    monkeypatch.setattr("letmegetin.core.rate_limit.time.monotonic", lambda: now)
    limiter = InMemoryLimiter()
    await limiter.hit("key", 1, 60)
    assert not (await limiter.hit("key", 1, 60)).allowed

    now = 61.0

    again = await limiter.hit("key", 1, 60)
    assert again.allowed
    assert again.remaining == 0


async def test_redis_backend_uses_the_shared_counter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fakeredis.aioredis import FakeRedis

    from letmegetin.core.rate_limit import check_rate_limit

    fake = FakeRedis(decode_responses=True)
    monkeypatch.setattr("letmegetin.core.rate_limit.get_redis", lambda: fake)

    first = await check_rate_limit("redis-key", 1)
    second = await check_rate_limit("redis-key", 1)

    assert first.allowed
    assert not second.allowed
    assert second.remaining == 0
