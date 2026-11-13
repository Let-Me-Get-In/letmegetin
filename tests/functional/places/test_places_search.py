"""Place search/candidates/detail integration test against the real PostGIS database.

Skips cleanly when the container or migration 0003 is absent.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from itertools import groupby
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text

from letmegetin.domain.places.dedup import normalize_name
from letmegetin.domain.places.entities import make_slug
from tests.db import SessionLocal, engine, require_database

_ORIGIN = (45.0, 5.0)
# Far from _ORIGIN and from any real AccesLibre row, so the bulk page tests see
# exactly the 150 seeded rows even on a national dev database.
_BULK_ORIGIN = (30.0, 4.0)
_BULK_COUNT = 150
_PLACES = [
    ("test-search-alpha", "Test Café Alpha", 45.0010, 5.0000),
    ("test-search-beta", "Test Librairie Beta", 45.0030, 5.0000),
    ("test-search-gamma", "Test Pharmacie Gamma", 45.0100, 5.0000),
]


async def _cleanup() -> None:
    async with SessionLocal() as session:
        await session.execute(text("DELETE FROM place WHERE source = 'test-search'"))
        await session.execute(text("DELETE FROM categories WHERE slug LIKE 'test-search-%'"))
        await session.execute(text("DELETE FROM criteria WHERE slug LIKE 'test-search-%'"))
        await session.commit()


async def _seed() -> None:
    async with SessionLocal() as session:
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
                "INSERT INTO place (source, source_id, name, name_normalized, slug, lat, lng) "
                "VALUES ('test-search', 'test-search-delta', 'Test Cabinet Delta', "
                ":normalized, :slug, 45.10, 5.0)"
            ),
            {
                "normalized": normalize_name("Test Cabinet Delta"),
                "slug": make_slug("Test Cabinet Delta", "test-search", "test-search-delta"),
            },
        )
        await session.execute(
            text(
                "INSERT INTO categories (slug, name, label) VALUES "
                "('test-search-pharmacie', 'Pharmacie', '{}'), "
                "('test-search-librairie', 'Librairie', '{}')"
            )
        )
        await session.execute(
            text(
                "UPDATE place SET category_id = (SELECT id FROM categories "
                "WHERE slug = 'test-search-pharmacie') WHERE source_id = 'test-search-gamma'"
            )
        )
        # Beta owns one answerable grid leaf, so the detail endpoint exercises the
        # documentation ladder end to end (the record is complete on its only criterion).
        await session.execute(
            text(
                "UPDATE place SET category_id = (SELECT id FROM categories "
                "WHERE slug = 'test-search-librairie') WHERE source_id = 'test-search-beta'"
            )
        )
        await session.execute(
            text(
                "INSERT INTO category_grid (category_id, version, tree) SELECT id, 1, "
                "CAST(:tree AS jsonb) FROM categories WHERE slug = 'test-search-librairie'"
            ),
            {
                "tree": json.dumps(
                    [
                        {
                            "slug": "test-search-step",
                            "label": {"fr": "Marche"},
                            "type": "boolean",
                            "handicap_families": ["moteur"],
                            "children": [],
                        }
                    ]
                )
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
                "INSERT INTO place_accessibility (place_id, criterion_id, value, source, actor) "
                "SELECT p.id, c.id, CAST(:value AS jsonb), 'test-search', 'test' "
                "FROM place p, criteria c "
                "WHERE p.source_id = 'test-search-beta' AND c.slug = 'test-search-step'"
            ),
            {"value": json.dumps({"value": True})},
        )
        await session.execute(
            text(
                "INSERT INTO place_accessibility (place_id, criterion_id, value, source, actor) "
                "SELECT p.id, c.id, CAST(:value AS jsonb), 'test-search', 'test' "
                "FROM place p, criteria c "
                "WHERE p.source_id = 'test-search-gamma' AND c.slug = 'test-search-loop'"
            ),
            {"value": json.dumps({"value": True})},
        )
        # Delta holds both criteria, so the AND test has one place that passes it and
        # beta/gamma each fail exactly one of them.
        await session.execute(
            text(
                "INSERT INTO place_accessibility (place_id, criterion_id, value, source, actor) "
                "SELECT p.id, c.id, CAST(:value AS jsonb), 'test-search', 'test' "
                "FROM place p, criteria c "
                "WHERE p.source_id = 'test-search-delta' "
                "AND c.slug IN ('test-search-step', 'test-search-loop')"
            ),
            {"value": json.dumps({"value": True})},
        )
        await session.execute(
            text(
                "INSERT INTO place (source, source_id, name, name_normalized, slug, lat, lng, "
                "category_id) "
                "SELECT 'test-search', 'test-search-bulk-' || i, 'Test Bulk ' || i, "
                "'test bulk ' || i, 'test-search-bulk-' || i, "
                # Ten coordinates, fifteen rows each: identical coordinates force the
                # distance ties that a plain ORDER BY could not page deterministically.
                ":lat + mod(i, 10) * 0.001, :lng + mod(i, 10) * 0.001, "
                # A shared category with a grid, so the batched documentation reads are
                # exercised on a 100-hit page as well as on a one-hit one.
                "(SELECT id FROM categories WHERE slug = 'test-search-librairie') "
                "FROM generate_series(1, :count) AS i"
            ),
            {"lat": _BULK_ORIGIN[0], "lng": _BULK_ORIGIN[1], "count": _BULK_COUNT},
        )
        await session.commit()


async def _criterion_id(slug: str) -> int:
    async with SessionLocal() as session:
        return int(
            await session.scalar(text("SELECT id FROM criteria WHERE slug = :slug"), {"slug": slug})
        )


async def _bulk_ids() -> dict[str, int]:
    async with SessionLocal() as session:
        rows = await session.execute(
            text(
                "SELECT slug, id FROM place "
                "WHERE source = 'test-search' AND source_id LIKE 'test-search-bulk-%'"
            )
        )
        return {str(slug): int(place_id) for slug, place_id in rows}


@pytest.fixture
def db(test_sessions: None) -> Iterator[None]:
    require_database("place")
    asyncio.run(_cleanup())
    asyncio.run(_seed())
    yield
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


def test_search_and_combines_two_criteria(client: TestClient) -> None:
    step = asyncio.run(_criterion_id("test-search-step"))
    loop = asyncio.run(_criterion_id("test-search-loop"))

    body = _search(client, radius=20000, filters=f"{step},{loop}")

    # Beta holds step only, gamma loop only, delta both: OR would return all three.
    assert [item["name"] for item in body] == ["Test Cabinet Delta"]


def test_search_dedupes_repeated_criterion_ids(client: TestClient) -> None:
    step = asyncio.run(_criterion_id("test-search-step"))

    once = _search(client, radius=5000, filters=str(step))
    twice = _search(client, radius=5000, filters=f"{step},{step}")

    assert twice == once


@pytest.mark.parametrize(
    "params",
    [{"family": "auditif"}, {"category": "test-search-pharmacie"}],
    ids=["handicap-family", "category"],
)
def test_search_filters_on_family_and_category(client: TestClient, params: dict[str, str]) -> None:
    body = _search(client, radius=5000, **params)

    assert [item["name"] for item in body] == ["Test Pharmacie Gamma"]


@pytest.mark.parametrize(
    "params",
    [{"category": "does-not-exist"}, {"family": "olfactif"}, {"offset": 20_000}],
    ids=["unknown-category", "unknown-family", "offset-beyond-cap"],
)
def test_search_rejects_invalid_filters(client: TestClient, params: dict[str, Any]) -> None:
    response = client.get(
        "/api/v1/places",
        params={"lat": _ORIGIN[0], "lng": _ORIGIN[1], **params},
    )

    assert response.status_code == 422


def test_search_omits_documentation_unless_asked(client: TestClient) -> None:
    body = _search(client, radius=5000)

    assert body
    # D-07: an existing consumer pays nothing until it passes the flag.
    assert all("documentation" not in item for item in body)


def test_search_returns_documentation_when_asked(client: TestClient) -> None:
    body = _search(client, radius=5000, with_documentation="true")

    by_name = {item["name"]: item["documentation"] for item in body}
    # Beta's category grid has one leaf and Beta answers it; gamma's category has no grid at all.
    assert by_name["Test Librairie Beta"] == {"rate": 1.0, "percent": 100, "level": "complete"}
    assert by_name["Test Pharmacie Gamma"] == {"rate": 0.0, "percent": 0, "level": "none"}
    assert all(0.0 <= item["rate"] <= 1.0 for item in by_name.values())
    assert {item["level"] for item in by_name.values()} <= {
        "none",
        "sketch",
        "partial",
        "good",
        "very_good",
        "complete",
    }


def test_search_keeps_an_undocumented_place(client: TestClient) -> None:
    without = _search(client, radius=5000)
    with_flag = _search(client, radius=5000, with_documentation="true")

    # D-06: rate 0.0 is a level, not an exclusion — same hits, same order.
    assert [item["slug"] for item in with_flag] == [item["slug"] for item in without]
    assert {item["documentation"]["level"] for item in with_flag} >= {"none", "complete"}


def test_search_with_documentation_stays_a_bare_array(client: TestClient) -> None:
    response = client.get(
        "/api/v1/places",
        params={
            "lat": _ORIGIN[0],
            "lng": _ORIGIN[1],
            "radius": 5000,
            "with_documentation": "true",
        },
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


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
    assert body["documentation"] == {"rate": 1.0, "percent": 100, "level": "complete"}
    assert body["accessibility_by_family"] == {
        "moteur": {"rate": 1.0, "percent": 100, "level": "complete"}
    }
    # No visuel leaf in the grid: absent, not a false "0 % documented" (D-12).
    assert "visuel" not in body["accessibility_by_family"]
    # The ladder the legend reads: one server source for the six slugs and their bounds.
    assert body["documentation_ladder"] == [
        {"slug": "none", "min": 0, "max": 0},
        {"slug": "sketch", "min": 1, "max": 25},
        {"slug": "partial", "min": 26, "max": 50},
        {"slug": "good", "min": 51, "max": 75},
        {"slug": "very_good", "min": 76, "max": 99},
        {"slug": "complete", "min": 100, "max": 100},
    ]


def test_place_detail_is_404_when_missing(client: TestClient) -> None:
    response = client.get("/api/v1/places/does-not-exist")

    assert response.status_code == 404


def _bulk_search(client: TestClient, **params: Any) -> list[dict[str, Any]]:
    return _search(client, lat=_BULK_ORIGIN[0], lng=_BULK_ORIGIN[1], radius=5000, **params)


def test_search_pages_beyond_one_hundred(client: TestClient) -> None:
    first = _bulk_search(client, limit=100)
    second = _bulk_search(client, limit=100, offset=100)

    assert len(first) == 100
    assert len(second) == _BULK_COUNT - 100
    slugs = [item["slug"] for item in first + second]
    assert len(set(slugs)) == _BULK_COUNT
    assert {item["slug"] for item in first}.isdisjoint({item["slug"] for item in second})


def test_search_order_is_stable_across_calls(client: TestClient) -> None:
    once = _bulk_search(client, limit=100)
    twice = _bulk_search(client, limit=100)

    assert [item["slug"] for item in once] == [item["slug"] for item in twice]

    # Every maximal run of equal distances is a tie group: it must be ordered by id,
    # which is what a bare ORDER BY distance could not promise.
    ids = asyncio.run(_bulk_ids())
    tie_groups = 0
    for _, group in groupby(once, key=lambda item: item["distance"]):
        rows = list(group)
        if len(rows) > 1:
            tie_groups += 1
            assert [ids[row["slug"]] for row in rows] == sorted(ids[row["slug"]] for row in rows)
    assert tie_groups > 0


def test_search_has_more_header(client: TestClient) -> None:
    query = {"lat": _BULK_ORIGIN[0], "lng": _BULK_ORIGIN[1], "radius": 5000}

    full_page = client.get("/api/v1/places", params={**query, "limit": 100})
    last_page = client.get("/api/v1/places", params={**query, "limit": 100, "offset": 100})
    past_end = client.get("/api/v1/places", params={**query, "limit": 100, "offset": 200})

    assert full_page.headers["X-Has-More"] == "true"
    assert last_page.headers["X-Has-More"] == "false"
    assert past_end.json() == []
    assert past_end.headers["X-Has-More"] == "false"


def _count_selects(client: TestClient, **params: Any) -> int:
    """SELECT statements the app's engine emits while serving one search request."""
    seen: list[str] = []

    def record(  # noqa: ANN001 - the SQLAlchemy listener signature is positional
        conn: Any, cursor: Any, statement: str, parameters: Any, context: Any, executemany: bool
    ) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            seen.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", record)
    try:
        _search(client, **params)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record)
    return len(seen)


def test_search_documentation_reads_do_not_scale_with_hits(client: TestClient) -> None:
    one_hit = {"radius": 500, "q": "beta"}
    many_hits = {"lat": _BULK_ORIGIN[0], "lng": _BULK_ORIGIN[1], "radius": 5000, "limit": 100}
    assert len(_search(client, **one_hit)) == 1
    assert len(_search(client, **many_hits)) == 100

    one_without = _count_selects(client, **one_hit)
    one_with = _count_selects(client, **one_hit, with_documentation="true")
    many_without = _count_selects(client, **many_hits)
    many_with = _count_selects(client, **many_hits, with_documentation="true")

    # The extra work is exactly the two batched reads, and it is the same two for 1 or
    # 100 hits: the documentation query never runs per hit (T-13-03).
    assert one_with - one_without == 2
    assert many_with - many_without == 2

    # The flag changes the payload, not just the read count.
    assert "documentation" in _search(client, **one_hit, with_documentation="true")[0]
    # The search response is not cached today. If a shared cache or CDN is introduced,
    # `with_documentation` must enter the ETag/Vary key (UI-SPEC, Data Contract: Caching).
