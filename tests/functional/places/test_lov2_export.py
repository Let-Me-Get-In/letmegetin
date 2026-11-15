"""Functional: the `lov2_partner` destination writes a partner archive, never a served one.

The licence gate is reviewed data (D-03, D-04): `lov2` leaves to a lov2 destination, `odbl` and
`cdla` never do, and the withheld rows are counted in the manifest rather than dropped silently.
The feed itself is keyed on AccesLibre's vocabulary (D-05..D-08): a row we cannot express lands in
the `mapping.csv` sidecar, never in the archive.
"""

from __future__ import annotations

import csv
import io
import json
import shutil
import zipfile
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.application.places.lov2_export import load_acceslibre_mapping
from letmegetin.config import settings
from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.acceslibre_map import FIELD_MAP, THEIR_FIELD_FOR_SLUG
from letmegetin.domain.places.entities import Place
from letmegetin.infrastructure.persistence.repositories import SqlAlchemyPlaceRepository
from tests.db import SessionLocal, execute, require_database, rows, run, scalar

_PREFIX = "cli-test-lov2-"
_PLACE_IDS = f"(SELECT id FROM place WHERE slug LIKE '{_PREFIX}%')"
_LOV2_SOURCE = "acceslibre"  # reviewed as lov2 in data/referential/source_licences.csv
_ODBL_SOURCE = f"{_PREFIX}odbl-source"
_CDLA_SOURCE = f"{_PREFIX}cdla-source"
_CATEGORY = f"{_PREFIX}category"
_CRITERION = f"{_PREFIX}crit"
_REIMPORT_PREFIX = "test-lov2-reimport-"
_REFERENTIAL = Path(__file__).resolve().parents[3] / "data/referential"
_INDEX = {"snapshot": {"name": "export-20261114-full.zip", "seq": 12}, "watermark": 12}


@pytest.fixture
def partner_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The reviewed data the feed reads, with a verified identifier rule instead of `blocked`.

    `_write_zip` also reads `licences.csv` for ATTRIBUTION, so the directory must hold it too —
    otherwise the export raises before writing anything.
    """
    data = tmp_path / "referential"
    data.mkdir()
    for name in (
        "licences.csv",
        "licence_destinations.csv",
        "source_licences.csv",
        "acceslibre_mapping.csv",
    ):
        shutil.copy(_REFERENTIAL / name, data / name)
    (data / "acceslibre_identifier_rule.csv").write_text(
        "rule;detail\norigin_id;VERIFIED\n", encoding="utf-8"
    )
    (data / "acceslibre_categories.csv").write_text(
        f"activite;category_slug;places\nTest activite;{_CATEGORY};10\n", encoding="utf-8"
    )
    monkeypatch.setattr(settings, "data_dir", data)
    return data


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
    execute(
        "DELETE FROM export_event WHERE entity_id IN "
        f"(SELECT id FROM place WHERE source_id LIKE '{_REIMPORT_PREFIX}%')"
    )
    execute(f"DELETE FROM place WHERE source_id LIKE '{_REIMPORT_PREFIX}%'")
    execute("DELETE FROM source_licence WHERE source LIKE :prefix", {"prefix": f"{_PREFIX}%"})
    execute("DELETE FROM criteria WHERE slug LIKE :prefix", {"prefix": f"{_PREFIX}%"})
    execute("DELETE FROM categories WHERE slug LIKE :prefix", {"prefix": f"{_PREFIX}%"})


def _seed() -> None:
    execute(
        "INSERT INTO categories (slug, name, label) VALUES (:slug, 'Test', '{}') "
        "ON CONFLICT (slug) DO NOTHING",
        {"slug": _CATEGORY},
    )
    execute(
        "INSERT INTO criteria (slug, parent_id, type, position, need_children, label, "
        "description) VALUES (:slug, NULL, 'boolean', 0, false, '{}', '{}') "
        "ON CONFLICT (slug) DO NOTHING",
        {"slug": _CRITERION},
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


async def _add(source: str, source_id: str | None, *, category: bool = False) -> Place:
    async with SessionLocal() as session:
        category_id = (
            await session.scalar(
                text("SELECT id FROM categories WHERE slug = :slug"), {"slug": _CATEGORY}
            )
            if category
            else None
        )
        place = await SqlAlchemyPlaceRepository(session).add(
            Place(
                id=0,
                name=f"Lieu {source_id or 'sans-id'}",
                slug=f"{_PREFIX}{source_id or 'sans-id'}",
                source=source,
                source_id=source_id,
                category_id=category_id,
            )
        )
        await session.commit()
        return place


async def _answer(place_id: int, values: dict[str, dict[str, object]], source: str) -> None:
    async with SessionLocal() as session:
        await SqlAlchemyPlaceRepository(session).upsert_accessibility(
            place_id, values, source=source, actor="test"
        )
        await session.commit()


async def _merge(alias_id: int, canonical_id: int) -> None:
    async with SessionLocal() as session:
        repository = SqlAlchemyPlaceRepository(session)
        place = await repository.get_by_id(alias_id)
        assert place is not None
        place.canonical_id = canonical_id
        await repository.update(place)
        await session.commit()


def _export_partner(out: Path) -> zipfile.ZipFile:
    invoked = CliRunner().invoke(
        admin.app,
        ["export", "odbl", "--destination", "lov2_partner", "--out", str(out)],
    )
    assert invoked.exit_code == 0, invoked.output
    archives = list(out.glob("lov2_partner-*-full.zip"))
    assert len(archives) == 1
    return zipfile.ZipFile(archives[0])


def _header(archive: zipfile.ZipFile, name: str) -> tuple[str, ...]:
    return tuple(next(csv.reader(io.StringIO(archive.read(name).decode("utf-8")))))


def _records(archive: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(archive.read(name).decode("utf-8"))))


def _mapping(out: Path) -> list[dict[str, str]]:
    with (out / "mapping.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def test_partner_archive_is_written_to_out_and_never_served(
    partner_data: Path,
    db: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
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


def test_lov2_feed_excludes_odbl_and_cdla(partner_data: Path, db: None, tmp_path: Path) -> None:
    lov2 = run(_add(_LOV2_SOURCE, "lov2"))
    odbl = run(_add(_ODBL_SOURCE, "odbl"))
    cdla = run(_add(_CDLA_SOURCE, "cdla"))

    with _export_partner(tmp_path) as archive:
        exported = {row["place_id"] for row in _records(archive, "places.csv")}
        manifest = json.loads(archive.read("manifest.json"))

    assert str(lov2.id) in exported
    assert str(odbl.id) not in exported
    assert str(cdla.id) not in exported

    withheld = {
        (entry["source"], entry["licence"]): entry["count"] for entry in manifest["excluded_places"]
    }
    assert withheld[(_ODBL_SOURCE, "odbl")] >= 1
    assert withheld[(_CDLA_SOURCE, "cdla")] >= 1


def test_cli_emits_partner_keys_in_every_entry(
    partner_data: Path, db: None, tmp_path: Path
) -> None:
    place = run(_add(_LOV2_SOURCE, "feed-1", category=True))
    merged = run(_add(_LOV2_SOURCE, "feed-2"))
    run(_merge(merged.id, place.id))
    run(
        _answer(
            place.id,
            {"entree-acces": {"value": "true", "source": _LOV2_SOURCE, "key": "entree_pmr"}},
            _LOV2_SOURCE,
        )
    )

    with _export_partner(tmp_path) as archive:
        places_header = _header(archive, "places.csv")
        categories_header = _header(archive, "categories.csv")
        criteria_header = _header(archive, "criteria.csv")
        answers_header = _header(archive, "answers.csv")
        aliases_header = _header(archive, "aliases.csv")
        places = [
            row for row in _records(archive, "places.csv") if row["place_id"] == str(place.id)
        ]
        answers = [
            row for row in _records(archive, "answers.csv") if row["place_id"] == str(place.id)
        ]
        aliases = [row for row in _records(archive, "aliases.csv") if row["alias_id"] == "feed-2"]
        categories = [
            row for row in _records(archive, "categories.csv") if row["activite"] == "Test activite"
        ]
        fields = {row["field"] for row in _records(archive, "criteria.csv")}

    forbidden = {"slug", "category_slug", "criterion_slug"}
    for header in (places_header, categories_header, criteria_header, answers_header):
        assert forbidden.isdisjoint(header), header
    assert {"identifier", "activite"} <= set(places_header)
    assert "field" in criteria_header and "field" in answers_header
    assert {"alias_id", "canonical_id"} <= set(aliases_header)

    assert places and places[0]["identifier"] == "feed-1"
    assert places[0]["activite"] == "Test activite"
    assert categories and categories[0]["name"] == "Test"
    assert fields == set(THEIR_FIELD_FOR_SLUG.values())
    assert answers and answers[0]["field"] == "entree_pmr"
    assert json.loads(answers[0]["value"]) == "true"
    assert aliases == [{"alias_id": "feed-2", "canonical_id": "feed-1"}]


def test_mapping_document_names_every_unmappable_place(
    partner_data: Path, db: None, tmp_path: Path
) -> None:
    anonymous = run(_add(_LOV2_SOURCE, None))
    place = run(_add(_LOV2_SOURCE, "unmappable-answer"))
    run(
        _answer(
            place.id,
            {_CRITERION: {"value": "true", "source": _LOV2_SOURCE, "key": "unknown"}},
            _LOV2_SOURCE,
        )
    )

    with _export_partner(tmp_path) as archive:
        places = _records(archive, "places.csv")
        identifiers = {row["identifier"] for row in places}
        answers = _records(archive, "answers.csv")

    mapping = _mapping(tmp_path)
    assert str(anonymous.id) not in {row["place_id"] for row in places}
    assert "unmappable-answer" in identifiers
    assert any(row["entity"] == "place" and row["reason"] == "no_identifier" for row in mapping), (
        mapping
    )
    assert any(
        row["entity"] == "criterion" and row["identifier"] == _CRITERION for row in mapping
    ), mapping
    assert not [row for row in answers if row["place_id"] == str(place.id)]


def test_every_db_criterion_is_in_the_mapping_document(db: None) -> None:
    documented = {
        row.identifier
        for row in load_acceslibre_mapping(_REFERENTIAL / "acceslibre_mapping.csv")
        if row.entity == "criterion"
    }
    in_database = {str(row[0]) for row in rows("SELECT slug FROM criteria")}
    # Test fixtures seed their own criterion; the reviewed document covers the referential only.
    referential = {slug for slug in in_database if not slug.startswith(_PREFIX)}

    assert len(referential) > 10
    assert referential - set(FIELD_MAP.values()) <= documented
    assert documented.isdisjoint(FIELD_MAP.values())


def test_partner_feed_refuses_a_delta(partner_data: Path, db: None, tmp_path: Path) -> None:
    invoked = CliRunner().invoke(
        admin.app,
        ["export", "odbl", "--destination", "lov2_partner", "--delta", "--out", str(tmp_path)],
    )

    assert invoked.exit_code == 1
    assert "full snapshots only" in invoked.output


def test_blocked_rule_diverts_every_place(partner_data: Path, db: None, tmp_path: Path) -> None:
    (partner_data / "acceslibre_identifier_rule.csv").write_text(
        "rule;detail\nblocked;UNVERIFIED\n", encoding="utf-8"
    )
    run(_add(_LOV2_SOURCE, "blocked"))

    with _export_partner(tmp_path) as archive:
        places = _records(archive, "places.csv")

    assert places == []
    assert any(
        row["entity"] == "place" and row["reason"] == "identifier_unresolved"
        for row in _mapping(tmp_path)
    )


_IMPORT_HEADER = "id;nom;commune;code_postal;latitude;longitude;categorie;entree_pmr\n"
_IMPORT_WITHOUT_SLUG = (
    _IMPORT_HEADER
    + f"{_REIMPORT_PREFIX}1;Lieu Reprise;Testville;99001;45.5;5.5;bibliotheque;true\n"
)
_IMPORT_WITH_SLUG = (
    "id;nom;slug;commune;code_postal;latitude;longitude;categorie;entree_pmr\n"
    f"{_REIMPORT_PREFIX}1;Lieu Reprise;lieu-reprise-123;Testville;99001;"
    "45.5;5.5;bibliotheque;true\n"
)


def test_reimport_preserves_owned_answers_and_fills_the_erp_slug(
    partner_data: Path, db: None, tmp_path: Path
) -> None:
    path = tmp_path / "acceslibre.csv"
    path.write_text(_IMPORT_WITHOUT_SLUG, encoding="utf-8")
    _import(path)
    place_id = scalar(
        "SELECT id FROM place WHERE source_id = :source_id", {"source_id": f"{_REIMPORT_PREFIX}1"}
    )
    assert scalar("SELECT erp_slug FROM place WHERE id = :id", {"id": place_id}) is None
    run(
        _answer(
            place_id,
            {"entree-acces": {"value": "false", "source": "user", "user_id": 1}},
            "user",
        )
    )

    path.write_text(_IMPORT_WITH_SLUG, encoding="utf-8")
    _import(path)

    assert (
        scalar("SELECT erp_slug FROM place WHERE id = :id", {"id": place_id}) == "lieu-reprise-123"
    )
    kept = rows(
        "SELECT pa.source, pa.value->>'value' FROM place_accessibility pa "
        "JOIN criteria c ON c.id = pa.criterion_id "
        "WHERE pa.place_id = :id AND c.slug = 'entree-acces'",
        {"id": place_id},
    )
    assert [(str(source), str(value)) for source, value in kept] == [("user", "false")]


def _import(path: Path) -> str:
    result = CliRunner().invoke(admin.app, ["import", "acceslibre", "--file", str(path)])
    assert result.exit_code == 0, result.output
    return result.output


def test_the_mapping_loader_fails_closed(tmp_path: Path) -> None:
    truncated = tmp_path / "truncated.csv"
    truncated.write_text("entity;identifier;reason;detail\ncriterion;only-two\n", encoding="utf-8")
    duplicate = tmp_path / "duplicate.csv"
    duplicate.write_text(
        "entity;identifier;reason;detail\n"
        "criterion;entree;not_expressible;why\n"
        "criterion;entree;not_expressible;why\n",
        encoding="utf-8",
    )

    with pytest.raises(DomainError):
        load_acceslibre_mapping(truncated)
    with pytest.raises(DomainError):
        load_acceslibre_mapping(duplicate)
