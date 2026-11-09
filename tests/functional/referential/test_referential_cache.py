"""The referential reads use the Redis cache when it is configured."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from fakeredis.aioredis import FakeRedis
from fastapi.testclient import TestClient

import letmegetin.core.redis as redis_module
from letmegetin.config import settings
from tests.db import require_database


@pytest.fixture
def db(test_sessions: None) -> Iterator[None]:
    require_database("categories")
    yield


def test_categories_are_written_to_the_versioned_cache(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeRedis(decode_responses=True)
    monkeypatch.setattr(settings, "redis_url", "redis://fake")
    monkeypatch.setattr(redis_module, "_client", fake)

    assert client.get("/api/v1/categories").status_code == 200

    keys = asyncio.run(fake.keys("ref:*:categories"))
    assert keys, "the categories read should populate the cache"

    assert client.get("/api/v1/categories").status_code == 200
