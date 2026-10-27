"""Category grid integration test: precomputed tree, ETag and 304 (real PostGIS)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from letmegetin import seed as seed_module
from letmegetin.config import settings
from letmegetin.core.db import get_session
from letmegetin.main import app

_engine = create_async_engine(settings.database_url, poolclass=NullPool)
_TestSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)


async def _database_ready() -> bool:
    try:
        async with _TestSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            table = await session.scalar(text("SELECT to_regclass('category_grid')"))
            return table is not None
    except Exception:  # noqa: BLE001 - any connection failure means "skip"
        return False


async def _override() -> AsyncIterator[AsyncSession]:
    async with _TestSessionLocal() as session:
        yield session


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    if not asyncio.run(_database_ready()):
        pytest.skip("PostGIS database or category_grid table unavailable")
    monkeypatch.setattr(seed_module, "SessionLocal", _TestSessionLocal)
    asyncio.run(seed_module.seed())
    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_category_grid_is_served_with_an_etag(client: TestClient) -> None:
    response = client.get("/api/v1/categories/restaurant/grid")

    assert response.status_code == 200
    assert response.headers["etag"].startswith('W/"ref-')
    assert "max-age" in response.headers["cache-control"]
    body = response.json()
    assert body["category"] == "restaurant"
    assert isinstance(body["version"], int)
    assert any(node["children"] for node in body["tree"])


def test_category_grid_returns_304_when_unchanged(client: TestClient) -> None:
    first = client.get("/api/v1/categories/restaurant/grid")
    etag = first.headers["etag"]

    second = client.get("/api/v1/categories/restaurant/grid", headers={"If-None-Match": etag})

    assert second.status_code == 304


def test_category_grid_is_404_for_an_unknown_category(client: TestClient) -> None:
    response = client.get("/api/v1/categories/unknown-category/grid")

    assert response.status_code == 404
