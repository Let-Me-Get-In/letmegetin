"""Reviews, photos and accessibility-tree integration tests against the real database.

Skips cleanly when the container or migration 0004 is absent.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from letmegetin.config import settings
from letmegetin.core.db import get_session
from letmegetin.domain.places.dedup import normalize_name
from letmegetin.main import app

_engine = create_async_engine(settings.database_url, poolclass=NullPool)
_TestSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

_SLUG = "test-p4-place-00000000"
_TREE = [
    {
        "slug": "test-p4-group",
        "label": {"fr": "Groupe"},
        "type": "array",
        "children": [
            {"slug": "test-p4-a", "label": {"fr": "A"}, "type": "boolean", "children": []},
            {"slug": "test-p4-b", "label": {"fr": "B"}, "type": "boolean", "children": []},
        ],
    }
]


async def _database_ready() -> bool:
    try:
        async with _TestSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return await session.scalar(text("SELECT to_regclass('review')")) is not None
    except Exception:  # noqa: BLE001 - any connection failure means "skip"
        return False


async def _cleanup() -> None:
    async with _TestSessionLocal() as session:
        await session.execute(
            text(
                "DELETE FROM review WHERE place_id IN "
                "(SELECT id FROM place WHERE source = 'test-p4')"
            )
        )
        await session.execute(
            text(
                "DELETE FROM place_photo WHERE place_id IN "
                "(SELECT id FROM place WHERE source = 'test-p4')"
            )
        )
        await session.execute(text("DELETE FROM place WHERE source = 'test-p4'"))
        await session.execute(
            text(
                "DELETE FROM place_accessibility WHERE criterion_id IN "
                "(SELECT id FROM criteria WHERE slug LIKE 'test-p4-%')"
            )
        )
        await session.execute(text("DELETE FROM criteria WHERE slug LIKE 'test-p4-%'"))
        await session.execute(
            text(
                "DELETE FROM category_grid WHERE category_id IN "
                "(SELECT id FROM categories WHERE slug = 'test-p4-cat')"
            )
        )
        await session.execute(text("DELETE FROM categories WHERE slug = 'test-p4-cat'"))
        await session.commit()


async def _seed() -> None:
    async with _TestSessionLocal() as session:
        category_id = await session.scalar(
            text(
                "INSERT INTO categories (slug, name, label) "
                "VALUES ('test-p4-cat', 'Test', '{}') RETURNING id"
            )
        )
        await session.execute(
            text(
                "INSERT INTO category_grid (category_id, version, tree) "
                "VALUES (:category_id, 1, CAST(:tree AS jsonb))"
            ),
            {"category_id": category_id, "tree": json.dumps(_TREE)},
        )
        place_id = await session.scalar(
            text(
                "INSERT INTO place (source, source_id, name, name_normalized, slug, "
                "category_id, lat, lng) VALUES ('test-p4', 'test-p4-1', 'Test Phase Quatre', "
                ":normalized, :slug, :category_id, 45.0, 5.0) RETURNING id"
            ),
            {
                "normalized": normalize_name("Test Phase Quatre"),
                "slug": _SLUG,
                "category_id": category_id,
            },
        )
        await session.execute(
            text(
                "INSERT INTO criteria (slug, parent_id, type, position, need_children, label, "
                "description) VALUES ('test-p4-a', NULL, 'boolean', 0, false, '{}', '{}'), "
                "('test-p4-b', NULL, 'boolean', 1, false, '{}', '{}')"
            )
        )
        await session.execute(
            text(
                "INSERT INTO place_accessibility (place_id, criterion_id, value) "
                "SELECT :place_id, id, CAST(:value AS jsonb) FROM criteria WHERE slug = 'test-p4-a'"
            ),
            {"place_id": place_id, "value": json.dumps({"value": True})},
        )
        await session.execute(
            text(
                "INSERT INTO place_photo (place_id, url, credit, license) "
                "VALUES (:place_id, 'https://example.test/photo.jpg', 'Acceslibre', 'Etalab 2.0')"
            ),
            {"place_id": place_id},
        )
        await session.execute(
            text(
                "INSERT INTO review (place_id, rating, body, author_name, status, created) VALUES "
                "(:place_id, 5, 'Très bien', 'Alice', 'published', now() - interval '2 hours'), "
                "(:place_id, 3, 'Moyen', 'Bob', 'published', now() - interval '1 hour'), "
                "(:place_id, 1, 'Masqué', 'Eve', 'hidden', now())"
            ),
            {"place_id": place_id},
        )
        await session.commit()


async def _override() -> AsyncIterator[AsyncSession]:
    async with _TestSessionLocal() as session:
        yield session


@pytest.fixture
def client() -> Iterator[TestClient]:
    if not asyncio.run(_database_ready()):
        pytest.skip("database or review table unavailable")
    asyncio.run(_cleanup())
    asyncio.run(_seed())
    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()
    asyncio.run(_cleanup())


def test_place_detail_returns_the_tree_values_and_completion(client: TestClient) -> None:
    body = client.get(f"/api/v1/places/{_SLUG}").json()

    assert body["filled_rate"] == 0.5
    assert body["rating"] == 4.0
    assert body["review_count"] == 2
    assert body["photos"][0]["url"] == "https://example.test/photo.jpg"
    assert [child["value"] for child in body["tree"][0]["children"]] == [{"value": True}, None]


def test_reviews_are_paginated_newest_first_and_skip_hidden(client: TestClient) -> None:
    first = client.get(f"/api/v1/places/{_SLUG}/reviews?page=1&size=1").json()
    second = client.get(f"/api/v1/places/{_SLUG}/reviews?page=2&size=1").json()

    assert (first["total"], first["page"], first["size"]) == (2, 1, 1)
    assert [item["rating"] for item in first["items"]] == [3]
    assert [item["rating"] for item in second["items"]] == [5]


def test_reviews_are_404_when_the_place_is_missing(client: TestClient) -> None:
    assert client.get("/api/v1/places/nope/reviews").status_code == 404
