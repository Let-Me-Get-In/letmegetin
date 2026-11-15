"""Functional: the `lov2_partner` destination writes a partner archive, never a served one.

The licence gate is reviewed data (D-03, D-04): `lov2` leaves to a lov2 destination, `odbl` and
`cdla` never do, and the withheld rows are counted in the manifest rather than dropped silently.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.config import settings
from letmegetin.domain.places.entities import Place
from letmegetin.infrastructure.persistence.repositories import SqlAlchemyPlaceRepository
from tests.db import SessionLocal, execute, require_database, run

_PREFIX = "cli-test-lov2-"
_PLACE_IDS = f"(SELECT id FROM place WHERE slug LIKE '{_PREFIX}%')"
_LOV2_SOURCE = "acceslibre"  # reviewed as lov2 in data/referential/source_licences.csv
_ODBL_SOURCE = f"{_PREFIX}odbl-source"
_CDLA_SOURCE = f"{_PREFIX}cdla-source"
_INDEX = {"snapshot": {"name": "export-20261114-full.zip", "seq": 12}, "watermark": 12}


@pytest.fixture
def db(test_sessions: None) -> Iterator[None]:
    require_database(
        "export_event", "place", "criteria", "categories", "licence", "licence_destination"
    )
    _cleanup()
    _seed()
    yield
    _cleanup()


def _cleanup() -> None:
    execute(f"DELETE FROM export_event WHERE entity_id IN {_PLACE_IDS}")
    execute(f"DELETE FROM place WHERE slug LIKE '{_PREFIX}%'")
    execute("DELETE FROM source_licence WHERE source LIKE :prefix", {"prefix": f"{_PREFIX}%"})
    execute("DELETE FROM criteria WHERE slug LIKE :prefix", {"prefix": f"{_PREFIX}%"})
    execute("DELETE FROM categories WHERE slug LIKE :prefix", {"prefix": f"{_PREFIX}%"})


def _seed() -> None:
    execute(
        "INSERT INTO categories (slug, name, label) VALUES (:slug, 'Test', '{}') "
        "ON CONFLICT (slug) DO NOTHING",
        {"slug": f"{_PREFIX}category"},
    )
    execute(
        "INSERT INTO criteria (slug, parent_id, type, position, need_children, label, "
        "description) VALUES (:slug, NULL, 'boolean', 0, false, '{}', '{}') "
        "ON CONFLICT (slug) DO NOTHING",
        {"slug": f"{_PREFIX}crit"},
    )
    # The reviewed matrix the export predicate reads (LIC-05).
    synced = CliRunner().invoke(admin.app, ["licences", "sync"])
    assert synced.exit_code == 0, synced.output
    # Two sources whose reviewed licence the lov2 matrix keeps out of a partner feed.
    for source, licence in ((_ODBL_SOURCE, "odbl"), (_CDLA_SOURCE, "cdla")):
        execute(
            "INSERT INTO source_licence (source, licence_slug, effective_from) "
            "VALUES (:source, :licence, :day) ON CONFLICT (source) DO UPDATE "
            "SET licence_slug = :licence",
            {"source": source, "licence": licence, "day": date(2020, 1, 1)},
        )


async def _add(source: str, source_id: str) -> Place:
    async with SessionLocal() as session:
        place = await SqlAlchemyPlaceRepository(session).add(
            Place(
                id=0,
                name=f"Lieu {source_id}",
                slug=f"{_PREFIX}{source_id}",
                source=source,
                source_id=source_id,
            )
        )
        await session.commit()
        return place


def _export_partner(out: Path) -> zipfile.ZipFile:
    invoked = CliRunner().invoke(
        admin.app,
        ["export", "odbl", "--destination", "lov2_partner", "--out", str(out)],
    )
    assert invoked.exit_code == 0, invoked.output
    archives = list(out.glob("lov2_partner-*-full.zip"))
    assert len(archives) == 1
    return zipfile.ZipFile(archives[0])


def test_partner_archive_is_written_to_out_and_never_served(
    db: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    served = tmp_path / "served"
    served.mkdir()
    (served / "latest.json").write_text(json.dumps(_INDEX), encoding="utf-8")
    monkeypatch.setattr(settings, "export_dir", served)
    out = tmp_path / "partner"
    out.mkdir()

    with _export_partner(out) as archive:
        assert {"places.csv", "manifest.json", "ATTRIBUTION.txt"} <= set(archive.namelist())
    partner_zip = next(out.glob("lov2_partner-*-full.zip"))
    index = json.loads((out / "latest.json").read_text(encoding="utf-8"))
    assert index["snapshot"]["name"] == partner_zip.name

    # The operator-chosen directory holds the archive; the served directory is untouched.
    assert not list(served.glob("*.zip"))
    assert json.loads((served / "latest.json").read_text(encoding="utf-8")) == _INDEX

    assert client.get(f"/api/v1/export/{partner_zip.name}").status_code == 404
    public_index = client.get("/api/v1/export/latest.json")
    assert public_index.status_code == 200
    assert public_index.json() == _INDEX


def test_lov2_feed_excludes_odbl_and_cdla(db: None, tmp_path: Path) -> None:
    lov2 = run(_add(_LOV2_SOURCE, "lov2"))
    odbl = run(_add(_ODBL_SOURCE, "odbl"))
    cdla = run(_add(_CDLA_SOURCE, "cdla"))

    with _export_partner(tmp_path) as archive:
        exported = {
            row["place_id"]
            for row in csv.DictReader(io.StringIO(archive.read("places.csv").decode("utf-8")))
        }
        manifest = json.loads(archive.read("manifest.json"))

    assert str(lov2.id) in exported
    assert str(odbl.id) not in exported
    assert str(cdla.id) not in exported

    withheld = {
        (entry["source"], entry["licence"]): entry["count"] for entry in manifest["excluded_places"]
    }
    assert withheld[(_ODBL_SOURCE, "odbl")] >= 1
    assert withheld[(_CDLA_SOURCE, "cdla")] >= 1
