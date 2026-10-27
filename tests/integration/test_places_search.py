"""Place search/candidates/detail integration test against the real PostGIS database.

Skips cleanly when the container or migration 0003 is absent.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from letmegetin.config import settings
from letmegetin.core.db import get_session
from letmegetin.domain.places.dedup import normalize_name
from letmegetin.domain.places.entities import make_slug
from letmegetin.main import app

# NullPool: the TestClient event loop differs from the test module's asyncio.run calls.
_engine = create_async_engine(settings.database_url, poolclass=NullPool)
_TestSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

_ORIGIN = (45.0, 5.0)
_PLACES = [
    ("test-search-alpha", "Test Café Alpha", 45.0010, 5.0000),
    ("test-search-beta", "Test Librairie Beta", 45.0030, 5.0000),
    ("test-search-gamma", "Test Pharmacie Gamma", 45.0100, 5.0000),
]


async def _database_ready() -> bool:
    try:
        async with _TestSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            table = await session.scalar(text("SELECT to_regclass('place')"))
            return table is not None
    except Exception:  # noqa: BLE001 - any connection failure means "skip"
        return False


async def _cleanup() -> None:
    async with _TestSessionLocal() as session:
        await session.execute(text("DELETE FROM place WHERE source = 'test-search'"))
        await session.execute(text("DELETE FROM criteria WHERE slug LIKE 'test-search-%'"))
        await session.commit()


async def _seed() -> None:
    async with _TestSessionLocal() as session:
        for source_id, name, lat, lng in _PLACES:
            await session.execute(
                text(
                    "INSERT INTO place (source, source_id, name, name_normalized, slug, lat, lng) "
                    "VALUES ('test-search', :source_id, :name, :normalized, :slug, :lat, :lng)"
                ),
                {
                    "source_id": source_id,
                    "name": name,
                    "normalized": normalize_name(name),
                    "slug": make_slug(name, "test-search", source_id),
                    "lat": lat,
                    "lng": lng,
                },
            )
        await session.execute(
            text(
                "INSERT INTO criteria (slug, parent_id, type, position, need_children, label, "
                "description, handicap_families) VALUES "
                "('test-search-step', NULL, 'boolean', 0, false, '{}', '{}', ARRAY['moteur']), "
                "('test-search-loop', NULL, 'boolean', 1, false, '{}', '{}', ARRAY['auditif'])"
            )
        )
        await session.execute(
            text(
                "INSERT INTO place_accessibility (place_id, criterion_id, value) "
                "SELECT p.id, c.id, CAST(:value AS jsonb) FROM place p, criteria c "
                "WHERE p.source_id = 'test-search-beta' AND c.slug = 'test-search-step'"
            ),
            {"value": json.dumps({"value": True})},
        )
        await session.execute(
            text(
                "INSERT INTO place_accessibility (place_id, criterion_id, value) "
                "SELECT p.id, c.id, CAST(:value AS jsonb) FROM place p, criteria c "
                "WHERE p.source_id = 'test-search-gamma' AND c.slug = 'test-search-loop'"
            ),
            {"value": json.dumps({"value": True})},
        )
        await session.commit()


async def _criterion_id(slug: str) -> int:
    async with _TestSessionLocal() as session:
        return int(
            await session.scalar(text("SELECT id FROM criteria WHERE slug = :slug"), {"slug": slug})
        )


async def _override() -> AsyncIterator[AsyncSession]:
    async with _TestSessionLocal() as session:
        yield session


@pytest.fixture
def client() -> Iterator[TestClient]:
    if not asyncio.run(_database_ready()):
        pytest.skip("PostGIS database or place table unavailable")
    asyncio.run(_cleanup())
    asyncio.run(_seed())
    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()
    asyncio.run(_cleanup())


def _search(client: TestClient, **params: Any) -> list[dict[str, Any]]:
    query = {"lat": _ORIGIN[0], "lng": _ORIGIN[1], **params}
    response = client.get("/api/v1/places", params=query)
    assert response.status_code == 200, response.text
    return response.json()


def test_search_is_distance_sorted(client: TestClient) -> None:
    body = _search(client, radius=5000)

    assert [item["name"] for item in body] == [
        "Test Café Alpha",
        "Test Librairie Beta",
        "Test Pharmacie Gamma",
    ]
    distances = [item["distance"] for item in body]
    assert distances == sorted(distances)
    assert body[0]["distance"] < body[1]["distance"]


def test_search_radius_bounds_the_results(client: TestClient) -> None:
    body = _search(client, radius=500)

    assert [item["name"] for item in body] == ["Test Café Alpha", "Test Librairie Beta"]


def test_search_filters_on_text(client: TestClient) -> None:
    body = _search(client, radius=5000, q="cafe")

    assert [item["name"] for item in body] == ["Test Café Alpha"]


def test_search_filters_on_criterion_ids(client: TestClient) -> None:
    criterion_id = asyncio.run(_criterion_id("test-search-step"))

    body = _search(client, radius=5000, filters=str(criterion_id))

    assert [item["name"] for item in body] == ["Test Librairie Beta"]


def test_search_filters_on_handicap_family(client: TestClient) -> None:
    body = _search(client, radius=5000, family="auditif")

    assert [item["name"] for item in body] == ["Test Pharmacie Gamma"]


def test_search_rejects_unknown_family(client: TestClient) -> None:
    response = client.get(
        "/api/v1/places", params={"lat": _ORIGIN[0], "lng": _ORIGIN[1], "family": "olfactif"}
    )

    assert response.status_code == 422


def test_candidates_return_near_duplicates(client: TestClient) -> None:
    response = client.get(
        "/api/v1/places/candidates",
        params={"lat": 45.0010, "lng": 5.0, "name": "Test Cafe Alpha"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["name"] == "Test Café Alpha"
    assert body[0]["score"] == 1.0
    assert body[0]["distance"] < 200


def test_place_detail_returns_the_accessibility_skeleton(client: TestClient) -> None:
    slug = make_slug("Test Librairie Beta", "test-search", "test-search-beta")

    response = client.get(f"/api/v1/places/{slug}")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Test Librairie Beta"
    assert body["lat"] == pytest.approx(45.0030)
    assert [item["criterion"] for item in body["accessibility"]] == ["test-search-step"]
    assert body["accessibility"][0]["handicap_families"] == ["moteur"]
    assert body["accessibility_by_family"]["moteur"] > 0
    assert body["accessibility_by_family"]["visuel"] == 0.0


def test_place_detail_is_404_when_missing(client: TestClient) -> None:
    response = client.get("/api/v1/places/does-not-exist")

    assert response.status_code == 404
