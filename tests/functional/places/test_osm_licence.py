"""Functional: an OSM row resolves its ODbL licence, and ODbL never reaches a lov2 partner.

Both facts are reviewed rows, not code (D-12, LIC-03): ``source_licences.csv`` maps ``osm`` to
``odbl``, and ``licence_destinations.csv`` already refuses ``odbl`` towards ``lov2_partner``. The
test owns the OSM licence assertions so a future matrix edit cannot open the forbidden path
without failing here.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.application.referential.licences import (
    load_licence_destinations,
    load_licences,
    load_source_licences,
)
from letmegetin.domain.places.licence import can_redistribute
from tests.db import execute, require_database, scalar, seed_source_licences
from tests.fixtures.osm_pbf import write_osm_pbf

_REFERENTIAL = Path(__file__).resolve().parents[3] / "data/referential"
_CLEANUP = "DELETE FROM place WHERE source = 'osm'"


@pytest.fixture
def db(test_sessions: None) -> Iterator[None]:
    require_database("place", "source_licence", "category_mapping")
    execute(_CLEANUP)
    yield
    execute(_CLEANUP)


@pytest.fixture
def osm_licence(test_sessions: None) -> None:
    """Load the reviewed source licences, exactly as ``seed`` does before an import."""
    seed_source_licences()


def test_an_imported_osm_row_carries_the_odbl_licence(
    db: None, osm_licence: None, tmp_path: Path
) -> None:
    path = tmp_path / "fixture.osm.pbf"
    write_osm_pbf(path)

    result = CliRunner().invoke(admin.app, ["import", "osm", "--file", str(path)])

    assert result.exit_code == 0, result.output
    assert scalar("SELECT source_license FROM place WHERE source = 'osm'") == "odbl"


def test_osm_answers_may_reach_osm_and_never_a_lov2_partner() -> None:
    slugs = {licence.slug for licence in load_licences(_REFERENTIAL / "licences.csv")}
    reviewed = load_licence_destinations(_REFERENTIAL / "licence_destinations.csv", slugs)
    matrix = {(row.licence_slug, row.destination): row.allowed for row in reviewed}
    sources = {
        row.source: row.licence_slug
        for row in load_source_licences(_REFERENTIAL / "source_licences.csv", slugs)
    }

    assert sources["osm"] == "odbl"
    assert can_redistribute("odbl", "osm", matrix) is True
    assert can_redistribute("odbl", "lov2_partner", matrix) is False
