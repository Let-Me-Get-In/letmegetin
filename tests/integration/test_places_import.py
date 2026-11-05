"""Acceslibre import integration test against the real PostGIS database.

Skips cleanly when the container or migration 0003 is absent.
"""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.application.places.import_acceslibre import iter_acceslibre_rows
from letmegetin.config import settings

# NullPool: each CLI invocation runs its own event loop via asyncio.run.
_engine = create_async_engine(settings.database_url, poolclass=NullPool)
_TestSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

_FIXTURE = (
    "id;nom;adresse;commune;code_postal;latitude;longitude;categorie;site_internet;"
    "telephone\n"
    "test-1;Médiathèque Test Alpha;1 rue des Tests;Testville;99001;45.1000;5.1000;"
    "Bibliothèque médiathèque;https://example.test;+33400000000\n"
    "test-2;Mediatheque Test Alpha;1 rue des Tests;Testville;99001;45.1000;5.1000;"
    "Bibliothèque médiathèque;;\n"
    "test-3;Mediatheque Test Alpha Annexe;1 rue des Tests;Testville;99001;45.1000;5.1000;"
    "Bibliothèque médiathèque;;\n"
)

_CATEGORY_FIXTURE = (
    "id;nom;adresse;commune;code_postal;latitude;longitude;categorie\n"
    "test-cat-1;Bibliothèque Test;1 rue des Tests;Testville;99001;45.3000;5.3000;"
    "Bibliothèque médiathèque\n"
    "test-cat-2;Musée Test;1 rue des Tests;Testville;99001;45.3100;5.3100;Musée\n"
    "test-cat-3;Château Imaginaire;1 rue des Tests;Testville;99001;45.3200;5.3200;"
    "Château imaginaire\n"
)


async def _database_ready() -> bool:
    try:
        async with _TestSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            table = await session.scalar(text("SELECT to_regclass('place')"))
            return table is not None
    except Exception:  # noqa: BLE001 - any connection failure means "skip"
        return False


async def _cleanup() -> None:
    async with _TestSessionLocal() as session:
        await session.execute(
            text("DELETE FROM place WHERE source = 'acceslibre' AND source_id LIKE 'test-%'")
        )
        await session.commit()


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    if not asyncio.run(_database_ready()):
        pytest.skip("PostGIS database or place table unavailable")
    asyncio.run(_cleanup())
    monkeypatch.setattr(admin, "SessionLocal", _TestSessionLocal)
    yield
    asyncio.run(_cleanup())


async def _query(statement: str) -> list[tuple]:
    async with _TestSessionLocal() as session:
        return list((await session.execute(text(statement))).all())


def _places(statement: str) -> list[tuple]:
    return asyncio.run(_query(statement))


def _import(path: Path, *extra: str) -> str:
    result = CliRunner().invoke(admin.app, ["import", "acceslibre", "--file", str(path), *extra])
    assert result.exit_code == 0, result.output
    return result.output


def test_acceslibre_import_is_idempotent_and_deduplicated(db: None, tmp_path: Path) -> None:
    path = tmp_path / "acceslibre.csv"
    path.write_text(_FIXTURE, encoding="utf-8")

    first = _import(path)
    assert "created=3" in first
    assert "linked=1" in first
    assert "review=1" in first

    second = _import(path)
    assert "created=0" in second
    assert "skipped=3" in second

    rows = _places(
        "SELECT source_id, canonical_id, operating_status FROM place "
        "WHERE source = 'acceslibre' AND source_id LIKE 'test-%' ORDER BY source_id"
    )
    assert [row[0] for row in rows] == ["test-1", "test-2", "test-3"]

    canonical, linked, review = rows[0][1], rows[1][1], rows[2]
    assert canonical is None
    assert linked is not None
    assert review[1] is None
    assert review[2] == "duplicate_review"


def test_acceslibre_import_logs_the_merge_and_keeps_the_alias(db: None, tmp_path: Path) -> None:
    path = tmp_path / "acceslibre.csv"
    path.write_text(_FIXTURE, encoding="utf-8")
    _import(path)

    merges = _places(
        "SELECT score FROM place_merge_log WHERE actor = 'acceslibre' "
        "AND kept_id IN (SELECT id FROM place WHERE source_id LIKE 'test-%')"
    )
    assert len(merges) == 1
    assert merges[0][0] > 0.9

    aliases = _places(
        "SELECT name FROM place_alias WHERE place_id = "
        "(SELECT id FROM place WHERE source_id = 'test-1')"
    )
    assert [row[0] for row in aliases] == ["Mediatheque Test Alpha"]


_ACCESSIBILITY_FIXTURE = (
    "id;nom;adresse;commune;code_postal;latitude;longitude;categorie;"
    "entree_pmr;entree_largeur_mini;photo_url\n"
    "test-p4-imp-1;Lieu Import Test;1 rue des Tests;Testville;99001;45.2;5.2;bibliotheque;"
    "true;90;https://example.test/p4.jpg\n"
)


def test_acceslibre_import_writes_accessibility_values_and_photos(db: None, tmp_path: Path) -> None:
    path = tmp_path / "acceslibre.csv"
    path.write_text(_ACCESSIBILITY_FIXTURE, encoding="utf-8")
    _import(path)

    values = _places(
        "SELECT c.slug, pa.value FROM place_accessibility pa "
        "JOIN criteria c ON c.id = pa.criterion_id "
        "JOIN place p ON p.id = pa.place_id WHERE p.source_id = 'test-p4-imp-1' "
        "ORDER BY c.position"
    )
    assert values == [
        ("entree-acces", {"value": "true", "source": "acceslibre", "key": "entree_pmr"}),
        (
            "entree-largeur-de-porte-cm",
            {"value": "90", "source": "acceslibre", "key": "entree_largeur_mini"},
        ),
    ]

    photos = _places(
        "SELECT url, credit FROM place_photo ph JOIN place p ON p.id = ph.place_id "
        "WHERE p.source_id = 'test-p4-imp-1'"
    )
    assert photos == [("https://example.test/p4.jpg", "Acceslibre")]

    updated = _ACCESSIBILITY_FIXTURE.replace(";true;90;", ";false;80;")
    path.write_text(updated, encoding="utf-8")
    _import(path)

    refreshed = _places(
        "SELECT pa.value->>'value' FROM place_accessibility pa "
        "JOIN criteria c ON c.id = pa.criterion_id "
        "JOIN place p ON p.id = pa.place_id "
        "WHERE p.source_id = 'test-p4-imp-1' AND c.slug = 'entree-acces'"
    )
    assert refreshed == [("false",)]
    assert (
        len(
            _places(
                "SELECT ph.id FROM place_photo ph JOIN place p ON p.id = ph.place_id "
                "WHERE p.source_id = 'test-p4-imp-1'"
            )
        )
        == 1
    )


def test_imported_categories_resolve_and_the_raw_value_is_kept(db: None, tmp_path: Path) -> None:
    path = tmp_path / "categories.csv"
    path.write_text(_CATEGORY_FIXTURE, encoding="utf-8")

    output = _import(path)

    assert "resolved=2" in output
    assert "unresolved=1" in output
    assert "unresolved: Château imaginaire=1" in output
    rows = _places(
        "SELECT p.source_id, c.slug, p.source_category FROM place p "
        "LEFT JOIN categories c ON c.id = p.category_id "
        "WHERE p.source_id LIKE 'test-cat-%' ORDER BY p.source_id"
    )
    assert rows == [
        ("test-cat-1", "library", "Bibliothèque médiathèque"),
        ("test-cat-2", "museum", "Musée"),
        ("test-cat-3", None, "Château imaginaire"),
    ]


def test_dry_run_reports_resolution_and_writes_nothing(db: None, tmp_path: Path) -> None:
    path = tmp_path / "categories.csv"
    path.write_text(_CATEGORY_FIXTURE, encoding="utf-8")

    output = _import(path, "--dry-run")

    assert "created=3" in output
    assert "dry_run=True" in output
    assert "resolved=2" in output
    assert "unresolved: Château imaginaire=1" in output
    assert _places("SELECT id FROM place WHERE source_id LIKE 'test-cat-%'") == []


def test_import_report_fails_while_a_category_is_unresolved(db: None, tmp_path: Path) -> None:
    path = tmp_path / "categories.csv"
    path.write_text(_CATEGORY_FIXTURE, encoding="utf-8")
    _import(path)

    result = CliRunner().invoke(admin.app, ["import", "report"])
    assert result.exit_code == 1, result.output
    assert "places by source: acceslibre=3" in result.output
    assert "Château imaginaire=1" in result.output
    assert "unresolved total=1 across 1 source values" in result.output

    asyncio.run(_delete_unresolved())

    clean = CliRunner().invoke(admin.app, ["import", "report"])
    assert clean.exit_code == 0, clean.output
    assert "unresolved total=0 across 0 source values" in clean.output


async def _delete_unresolved() -> None:
    async with _TestSessionLocal() as session:
        await session.execute(
            text("DELETE FROM place WHERE source_id LIKE 'test-cat-%' AND category_id IS NULL")
        )
        await session.commit()


def test_cli_streams_the_export_instead_of_building_a_list(
    db: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "categories.csv"
    path.write_text(_CATEGORY_FIXTURE, encoding="utf-8")
    rows = iter_acceslibre_rows(path)
    assert iter(rows) is rows  # a generator, not a materialised list

    def _boom(_: Path) -> list[object]:
        raise AssertionError("the CLI must not call load_acceslibre_file")

    module = importlib.import_module("letmegetin.application.places.import_acceslibre")
    monkeypatch.setattr(module, "load_acceslibre_file", _boom)
    assert "created=3" in _import(path)
