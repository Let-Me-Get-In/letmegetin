"""Functional: the `lov2_partner` destination writes its archive to the operator-chosen directory.

The public `/api/v1/export` routes read `settings.export_dir` only, so a partner archive that
lands elsewhere is never served (D-04, Pitfall 1).
"""

from __future__ import annotations

import json
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.config import settings
from tests.db import execute, require_database

_PREFIX = "cli-test-lov2-"
_PLACE_IDS = f"(SELECT id FROM place WHERE slug LIKE '{_PREFIX}%')"
_INDEX = {"snapshot": {"name": "export-20261114-full.zip", "seq": 12}, "watermark": 12}


@pytest.fixture
def db(test_sessions: None) -> Iterator[None]:
    require_database(
        "export_event", "place", "criteria", "categories", "licence", "licence_destination"
    )
    _cleanup()
    # The reviewed matrix the export predicate reads (LIC-05).
    synced = CliRunner().invoke(admin.app, ["licences", "sync"])
    assert synced.exit_code == 0, synced.output
    yield
    _cleanup()


def _cleanup() -> None:
    # export_event has no foreign key: prune it by hand, then the place cascade clears the rest.
    execute(f"DELETE FROM export_event WHERE entity_id IN {_PLACE_IDS}")
    execute(f"DELETE FROM place WHERE slug LIKE '{_PREFIX}%'")
    execute("DELETE FROM source_licence WHERE source LIKE :prefix", {"prefix": f"{_PREFIX}%"})
    execute("DELETE FROM criteria WHERE slug LIKE :prefix", {"prefix": f"{_PREFIX}%"})
    execute("DELETE FROM categories WHERE slug LIKE :prefix", {"prefix": f"{_PREFIX}%"})


def test_partner_archive_is_written_to_out_and_never_served(
    db: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    served = tmp_path / "served"
    served.mkdir()
    (served / "latest.json").write_text(json.dumps(_INDEX), encoding="utf-8")
    monkeypatch.setattr(settings, "export_dir", served)
    out = tmp_path / "partner"
    out.mkdir()

    invoked = CliRunner().invoke(
        admin.app,
        ["export", "odbl", "--destination", "lov2_partner", "--out", str(out)],
    )
    assert invoked.exit_code == 0, invoked.output

    with zipfile.ZipFile(next(out.glob("lov2_partner-*-full.zip"))) as archive:
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
