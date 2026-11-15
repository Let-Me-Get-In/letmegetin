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
from letmegetin.application.referential.osm_tags import HEADER as OSM_TAGS_HEADER
from letmegetin.config import settings
from tests.db import SessionLocal, execute, require_database, seed_source_licences
from tests.fixtures.osm_pbf import write_osm_pbf

_CLEANUP = "DELETE FROM place WHERE source = 'osm'"

_NODE_1_TAGS = {"amenity": "cafe", "name": "Café du Coin", "wheelchair": "yes"}
_CRITERION = "circulation-acces-en-fauteuil-a-tout-le-lieu"
_ANSWER = f"{_CRITERION}-acces-en-fauteuil-possible-partout"


@pytest.fixture
def db(test_sessions: None) -> Iterator[None]:
    require_database("place", "source_licence", "category_mapping")
    execute(_CLEANUP)
    yield
    execute(_CLEANUP)


@pytest.fixture
def osm_licence(test_sessions: None) -> None:
    """Load the reviewed source licences (``osm;odbl``), as ``seed`` does before an import."""
    seed_source_licences()


def _places(statement: str) -> list[tuple]:
    async def _query() -> list[tuple]:
        async with SessionLocal() as session:
            return list((await session.execute(text(statement))).all())

    return asyncio.run(_query())


def _import(path: Path, *extra: str) -> str:
    result = CliRunner().invoke(admin.app, ["import", "osm", "--file", str(path), *extra])
    assert result.exit_code == 0, result.output
    return result.output


def _pbf(tmp_path: Path, *, with_bakery: bool = False) -> Path:
    path = tmp_path / "fixture.osm.pbf"
    write_osm_pbf(path, with_bakery=with_bakery)
    return path


def _reviewed(data: Path, row: str) -> None:
    """Point the importer and the audit at a one-row accessibility mapping (bad on purpose)."""
    data.mkdir(exist_ok=True)
    (data / "osm_accessibility_tags.csv").write_text(
        f"{';'.join(OSM_TAGS_HEADER)}\n{row}\n", encoding="utf-8"
    )


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


def test_osm_import_writes_the_mapped_accessibility_value(
    db: None, osm_licence: None, tmp_path: Path
) -> None:
    _import(_pbf(tmp_path))

    rows = _places(
        "SELECT c.slug, pa.value, pa.source, pa.source_license FROM place_accessibility pa "
        "JOIN criteria c ON c.id = pa.criterion_id "
        "JOIN place p ON p.id = pa.place_id WHERE p.source = 'osm'"
    )

    assert rows == [
        (
            _CRITERION,
            {"value": _ANSWER, "source": "osm", "key": "wheelchair"},
            "osm",
            "odbl",
        )
    ]


def test_osm_import_still_writes_a_mapped_poi_without_accessibility_tags(
    db: None, osm_licence: None, tmp_path: Path
) -> None:
    output = _import(_pbf(tmp_path, with_bakery=True))

    assert "created=2" in output
    assert _places("SELECT id FROM place WHERE source = 'osm' AND source_id = 'node/3'") != []
    assert (
        _places(
            "SELECT pa.criterion_id FROM place_accessibility pa "
            "JOIN place p ON p.id = pa.place_id "
            "WHERE p.source = 'osm' AND p.source_id = 'node/3'"
        )
        == []
    )


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


@pytest.mark.parametrize(
    "row",
    [
        "wheelchair;yes;bogus_criterion;true",
        "wheelchair;yes;entree-acces;not-an-option",
    ],
    ids=["unknown-criterion", "illegal-option-value"],
)
def test_osm_import_refuses_an_incoherent_mapping(
    db: None,
    osm_licence: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    row: str,
) -> None:
    _reviewed(tmp_path / "referential", row)
    monkeypatch.setattr(settings, "data_dir", tmp_path / "referential")

    result = CliRunner().invoke(admin.app, ["import", "osm", "--file", str(_pbf(tmp_path))])

    assert result.exit_code == 1, result.output
    assert "osm accessibility mapping is not coherent" in result.output
    assert _places("SELECT id FROM place WHERE source = 'osm'") == []


def test_osm_audit_passes_on_the_reviewed_data(db: None) -> None:
    result = CliRunner().invoke(admin.app, ["osm", "audit"])

    assert result.exit_code == 0, result.output
    assert "osm tags ok" in result.output


def test_osm_audit_exits_one_on_an_incoherent_mapping(
    db: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _reviewed(tmp_path / "referential", "wheelchair;yes;bogus_criterion;true")
    monkeypatch.setattr(settings, "data_dir", tmp_path / "referential")

    result = CliRunner().invoke(admin.app, ["osm", "audit"])

    assert result.exit_code == 1, result.output
    assert "unknown criterion 'bogus_criterion'" in result.output
