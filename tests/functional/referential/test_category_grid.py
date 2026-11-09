"""Category grid integration test: precomputed tree, ETag and 304 (real PostGIS)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from letmegetin import seed as seed_module
from tests.db import require_database, run


@pytest.fixture
def db(test_sessions: None) -> Iterator[None]:
    require_database("category_grid")
    run(seed_module.seed())
    yield


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
