"""The referential reads use the Redis cache when it is configured."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator

import pytest
from fakeredis.aioredis import FakeRedis
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import letmegetin.core.redis as redis_module
from letmegetin.config import settings
from letmegetin.core.db import get_session
from letmegetin.main import app

_engine = create_async_engine(settings.database_url, poolclass=NullPool)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


async def _database_ready() -> bool:
    try:
        async with _Session() as session:
            await session.execute(text("SELECT 1"))
            return await session.scalar(text("SELECT to_regclass('categories')")) is not None
    except Exception:  # noqa: BLE001 - any connection failure means "skip"
        return False


async def _override() -> AsyncIterator[AsyncSession]:
    async with _Session() as session:
        yield session


@pytest.fixture
def client() -> Iterator[TestClient]:
    if not asyncio.run(_database_ready()):
        pytest.skip("database unavailable")
    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


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
