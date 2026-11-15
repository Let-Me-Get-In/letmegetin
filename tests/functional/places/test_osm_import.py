"""OpenStreetMap import functional test against the real PostGIS database.

Skips cleanly when the container or migration 0016 is absent.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import text
from typer.testing import CliRunner

from letmegetin import admin
from tests.db import SessionLocal, execute, require_database, scalar
from tests.fixtures.osm_pbf import write_osm_pbf

_CLEANUP = "DELETE FROM place WHERE source = 'osm'"

_NODE_1_TAGS = {"amenity": "cafe", "name": "Café du Coin", "wheelchair": "yes"}


@pytest.fixture
def db(test_sessions: None) -> Iterator[None]:
    require_database("place", "source_licence", "category_mapping")
    execute(_CLEANUP)
    yield
    execute(_CLEANUP)


@pytest.fixture
def osm_licence(test_sessions: None) -> Iterator[None]:
    """Stand in for the reviewed ``osm;odbl`` row the 16-02 CSV change adds.

    A place write snapshots its source licence and refuses an unmapped source (LIC-05), so
    the import cannot be proven before that row exists.
    """
    created = scalar("SELECT licence_slug FROM source_licence WHERE source = 'osm'") is None
    if created:
        execute(
            "INSERT INTO licence (slug, name, obligations) VALUES ('odbl', 'odbl', '[]'::jsonb) "
            "ON CONFLICT (slug) DO NOTHING"
        )
        execute(
            "INSERT INTO source_licence (source, licence_slug, effective_from) "
            "VALUES ('osm', 'odbl', '2026-11-15')"
        )
    yield
    if created:
        execute("DELETE FROM source_licence WHERE source = 'osm'")


def _places(statement: str) -> list[tuple]:
    async def _query() -> list[tuple]:
        async with SessionLocal() as session:
            return list((await session.execute(text(statement))).all())

    return asyncio.run(_query())


def _import(path: Path, *extra: str) -> str:
    result = CliRunner().invoke(admin.app, ["import", "osm", "--file", str(path), *extra])
    assert result.exit_code == 0, result.output
    return result.output


def _pbf(tmp_path: Path) -> Path:
    path = tmp_path / "fixture.osm.pbf"
    write_osm_pbf(path)
    return path


def test_osm_import_writes_one_place_with_version_and_raw_tags(
    db: None, osm_licence: None, tmp_path: Path
) -> None:
    output = _import(_pbf(tmp_path))

    assert "created=1" in output
    assert "resolved=1" in output
    assert "unresolved=2" in output
    assert "unmatched: name=Antiquités shop=antiques=1" in output
    assert "unmatched: highway=residential=1" in output

    rows = _places(
        "SELECT p.source_id, c.slug, p.source_category, p.osm_version, p.osm_tags, "
        "p.source_license, p.lat, p.lng FROM place p "
        "LEFT JOIN categories c ON c.id = p.category_id WHERE p.source = 'osm'"
    )
    assert len(rows) == 1
    source_id, category_slug, source_category, version, tags, licence, lat, lng = rows[0]
    assert source_id == "node/1"
    assert category_slug == "cafe"
    assert source_category == "amenity=cafe"
    assert version == 1
    assert tags == _NODE_1_TAGS
    assert licence == "odbl"
    assert (lat, lng) == (45.1, 5.1)


def test_osm_import_is_idempotent(db: None, osm_licence: None, tmp_path: Path) -> None:
    path = _pbf(tmp_path)
    _import(path)

    second = _import(path)

    assert "created=0" in second
    assert "skipped=1" in second
    assert len(_places("SELECT id FROM place WHERE source = 'osm'")) == 1


def test_osm_import_dry_run_writes_nothing(db: None, osm_licence: None, tmp_path: Path) -> None:
    output = _import(_pbf(tmp_path), "--dry-run")

    assert "created=1" in output
    assert "dry_run=True" in output
    assert _places("SELECT id FROM place WHERE source = 'osm'") == []


def test_osm_import_skips_unmapped_objects(db: None, osm_licence: None, tmp_path: Path) -> None:
    _import(_pbf(tmp_path))

    rows = _places(
        "SELECT source_id FROM place WHERE source = 'osm' AND source_id IN ('node/2', 'way/100')"
    )
    assert rows == []
