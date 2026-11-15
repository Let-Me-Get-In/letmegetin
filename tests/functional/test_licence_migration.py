"""Functional: the `dual` licence makes a NEW user contribution shippable to lov2_partner.

D-01/D-02 are reviewed data here, not code: `licences sync` loads `user -> dual` and the Phase 14
feed's licence predicate then lets a NEW user answer through while `odbl` and `cdla` answers stay
out. This is the feed itself (`answers.csv`), not a matrix query.

No re-stamp test lives here by design: the 2026-11-15 contributor-terms decision was `new-only`,
so existing `odbl` user rows are never re-licensed and no migration 0016 was written.
"""

from __future__ import annotations

import csv
import io
import shutil
import zipfile
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import text
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.config import settings
from letmegetin.domain.places.entities import Place
from letmegetin.infrastructure.persistence.repositories import SqlAlchemyPlaceRepository
from tests.db import SessionLocal, execute, require_database, run, scalar

_PREFIX = "dual-licence-"
_PLACE_IDS = f"(SELECT id FROM place WHERE slug LIKE '{_PREFIX}%')"
_PLACE_SOURCE = "acceslibre"  # reviewed as lov2, so the place itself may leave
_ODBL_SOURCE = f"{_PREFIX}odbl-source"
_CDLA_SOURCE = f"{_PREFIX}cdla-source"
_CRITERION = "entree-acces"  # FIELD_MAP -> entree_pmr
_CATEGORY = f"{_PREFIX}category"
_ACTIVITE = "Test activite dual"
_DUAL_NAME = "Licence Ouverte v2.0 (Etalab 2.0) + Open Database License 1.0"
_REFERENTIAL = Path(__file__).resolve().parents[2] / "data/referential"


@pytest.fixture
def licence_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The reviewed CSV the feed and `sync` read, with a verified `origin_id` rule pinned."""
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
        f"activite;category_slug;places\n{_ACTIVITE};{_CATEGORY};10\n", encoding="utf-8"
    )
    monkeypatch.setattr(settings, "data_dir", data)
    return data


@pytest.fixture
def db(licence_data: Path, test_sessions: None) -> Iterator[None]:
    require_database("source_licence", "place", "place_accessibility", "criteria", "categories")
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
        {"slug": _CATEGORY},
    )
    execute(
        "INSERT INTO criteria (slug, parent_id, type, position, need_children, label, "
        "description) VALUES (:slug, NULL, 'boolean', 0, false, '{}', '{}') "
        "ON CONFLICT (slug) DO NOTHING",
        {"slug": _CRITERION},
    )
    synced = CliRunner().invoke(admin.app, ["licences", "sync"])
    assert synced.exit_code == 0, synced.output
    for source, licence in ((_ODBL_SOURCE, "odbl"), (_CDLA_SOURCE, "cdla")):
        execute(
            "INSERT INTO source_licence (source, licence_slug, effective_from) "
            "VALUES (:source, :licence, :day) ON CONFLICT (source) DO UPDATE "
            "SET licence_slug = :licence",
            {"source": source, "licence": licence, "day": date(2020, 1, 1)},
        )


async def _add(source_id: str) -> Place:
    async with SessionLocal() as session:
        category_id = await session.scalar(
            text("SELECT id FROM categories WHERE slug = :slug"), {"slug": _CATEGORY}
        )
        place = await SqlAlchemyPlaceRepository(session).add(
            Place(
                id=0,
                name=f"Lieu {source_id}",
                slug=f"{_PREFIX}{source_id}",
                source=_PLACE_SOURCE,
                source_id=source_id,
                category_id=category_id,
            )
        )
        await session.commit()
        return place


async def _answer(place_id: int, source: str) -> None:
    async with SessionLocal() as session:
        await SqlAlchemyPlaceRepository(session).upsert_accessibility(
            place_id,
            {_CRITERION: {"value": "true", "source": source, "user_id": 1}},
            source=source,
            actor="test",
        )
        await session.commit()


def _export(out: Path) -> zipfile.ZipFile:
    invoked = CliRunner().invoke(
        admin.app,
        ["export", "odbl", "--destination", "lov2_partner", "--out", str(out)],
    )
    assert invoked.exit_code == 0, invoked.output
    archives = list(out.glob("lov2_partner-*-full.zip"))
    assert len(archives) == 1
    return zipfile.ZipFile(archives[0])


def test_new_user_answer_is_dual_and_reaches_the_lov2_feed(db: None, tmp_path: Path) -> None:
    user_place = run(_add("user"))
    odbl_place = run(_add("odbl"))
    cdla_place = run(_add("cdla"))
    run(_answer(user_place.id, "user"))
    run(_answer(odbl_place.id, _ODBL_SOURCE))
    run(_answer(cdla_place.id, _CDLA_SOURCE))

    stamped = scalar(
        "SELECT source_license FROM place_accessibility WHERE place_id = :id", {"id": user_place.id}
    )
    assert stamped == "dual"

    with _export(tmp_path) as archive:
        answers = list(csv.DictReader(io.StringIO(archive.read("answers.csv").decode("utf-8"))))
        attribution = archive.read("ATTRIBUTION.txt").decode("utf-8")

    exported = {row["place_id"]: row for row in answers}
    assert exported[str(user_place.id)]["field"] == "entree_pmr"
    assert exported[str(user_place.id)]["source_license"] == "dual"
    assert str(odbl_place.id) not in exported
    assert str(cdla_place.id) not in exported
    # D-02: the reviewed sentence names both licences, and the block lists it only because
    # a dual row was exported.
    assert _DUAL_NAME in attribution
