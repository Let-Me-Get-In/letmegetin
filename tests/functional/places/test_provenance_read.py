"""Functional tracer: provenance reaches ``GET /api/v1/places/{slug}`` (D-16, D-17).

One AccesLibre place and one of its answers are imported, then read back through the public
detail endpoint: the place shows the source's claimed date, never our ingestion time.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from letmegetin import admin
from tests.db import execute, require_database, scalar

_SOURCE_ID = "test-p12r-import"
_DATE_MAJ = datetime(2026, 3, 4, 10, 30)
_FIXTURE = (
    "id;nom;categorie;latitude;longitude;date_maj;entree_pmr\n"
    f"{_SOURCE_ID};Médiathèque Provenance;bibliotheque;45.2;5.2;2026-03-04T10:30:00;true\n"
)

_CLEANUP = "DELETE FROM place WHERE source_id LIKE 'test-p12r%'"


@pytest.fixture
def db(test_sessions: None, tmp_path: Path) -> Iterator[None]:
    require_database("place", "place_accessibility")
    execute(_CLEANUP)
    path = tmp_path / "acceslibre.csv"
    path.write_text(_FIXTURE, encoding="utf-8")
    result = CliRunner().invoke(admin.app, ["import", "acceslibre", "--file", str(path)])
    assert result.exit_code == 0, result.output
    yield
    execute(_CLEANUP)


def _slug() -> str:
    return scalar("SELECT slug FROM place WHERE source_id = :source_id", {"source_id": _SOURCE_ID})


def test_the_detail_endpoint_surfaces_provenance_on_the_place_and_each_answer(
    client: TestClient,
) -> None:
    response = client.get(f"/api/v1/places/{_slug()}")
    assert response.status_code == 200, response.text
    detail = response.json()

    assert detail["source"] == "acceslibre"
    assert detail["license"] == "lov2"
    assert datetime.fromisoformat(detail["observed_at"]) == _DATE_MAJ

    answer = next(item for item in detail["accessibility"] if item["criterion"] == "entree-acces")
    assert answer["source"] == "acceslibre"
    assert answer["license"] == "lov2"
    assert datetime.fromisoformat(answer["observed_at"]) == _DATE_MAJ


def test_the_search_list_carries_no_provenance_per_result(client: TestClient) -> None:
    results = client.get("/api/v1/places", params={"lat": 45.2, "lng": 5.2}).json()

    assert results
    assert all({"source", "license", "observed_at"}.isdisjoint(item) for item in results)
