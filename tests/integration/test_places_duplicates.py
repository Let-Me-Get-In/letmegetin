"""Duplicate review queue and coverage export against the real PostGIS database.

Skips cleanly when the container or the place table is absent. Only rows with a
``test-``/``cli-test-`` source id are written or deleted.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.config import settings
from letmegetin.core.db import get_session
from letmegetin.main import app

# NullPool: each CLI invocation runs its own event loop via asyncio.run.
_engine = create_async_engine(settings.database_url, poolclass=NullPool)
_TestSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

# Yields one auto-link (test-2, score 1.0) and one review candidate (test-3, ~0.85).
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

# Two countries, one place without values, one merged row and one unresolved category.
_COVERAGE_FIXTURE = (
    "id;nom;adresse;commune;code_postal;latitude;longitude;categorie;acces_entree\n"
    "cli-test-cov-1;Lieu Couverture Un;1 rue des Tests;Testville;99001;45.5000;5.5000;"
    "Bibliothèque médiathèque;true\n"
    "cli-test-cov-2;Lieu Couverture Deux;1 rue des Tests;Testville;99001;45.5100;5.5000;"
    "Bibliothèque médiathèque;\n"
    "cli-test-cov-3;Lieu Couverture Trois;1 rue des Tests;Testville;99001;45.5200;5.5000;"
    "Musée;true\n"
    "cli-test-cov-4;Lieu Couverture Quatre;1 rue des Tests;Testville;99001;45.5300;5.5000;"
    "Château imaginaire;true\n"
    "cli-test-cov-5;Lieu Couverture Cinq;1 rue des Tests;Testville;99001;45.5400;5.5000;"
    "Bibliothèque médiathèque;true\n"
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
            text(
                "DELETE FROM place WHERE source = 'acceslibre' "
                "AND (source_id LIKE 'test-%' OR source_id LIKE 'cli-test-%')"
            )
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


def _place_id(source_id: str) -> int:
    return int(_places(f"SELECT id FROM place WHERE source_id = '{source_id}'")[0][0])


def _cli(*args: str):
    return CliRunner().invoke(admin.app, list(args))


def _import(path: Path) -> None:
    result = _cli("import", "acceslibre", "--file", str(path))
    assert result.exit_code == 0, result.output


def _search() -> list[str]:
    async def _override() -> AsyncIterator[AsyncSession]:
        async with _TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = _override
    try:
        response = TestClient(app).get(
            "/api/v1/places", params={"lat": 45.1, "lng": 5.1, "radius": 500}
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    return [item["name"] for item in response.json()]


def test_duplicates_list_shows_the_review_row_with_its_score(db: None, tmp_path: Path) -> None:
    path = tmp_path / "acceslibre.csv"
    path.write_text(_FIXTURE, encoding="utf-8")
    _import(path)
    review_id = _place_id("test-3")

    result = _cli("duplicates", "list")

    assert result.exit_code == 0, result.output
    assert f"{review_id}\t" in result.output
    assert "Mediatheque Test Alpha Annexe -> Médiathèque Test Alpha" in result.output
    score = float(_places(f"SELECT confidence FROM place WHERE id = {review_id}")[0][0])
    assert 0.60 <= score < 0.90


def test_duplicates_list_flags_a_score_outside_the_review_band(db: None) -> None:
    asyncio.run(_seed_out_of_band())

    result = _cli("duplicates", "list")

    assert result.exit_code == 0, result.output
    line = [row for row in result.output.splitlines() if "Lieu Hors Bande Deux" in row]
    assert len(line) == 1
    assert line[0].endswith("[out of band]")


async def _seed_out_of_band() -> None:
    async with _TestSessionLocal() as session:
        await session.execute(
            text(
                "INSERT INTO place (source, source_id, name, name_normalized, slug) VALUES "
                "('acceslibre', 'cli-test-oob-1', 'Lieu Hors Bande Un', 'lieu hors bande un', "
                "'cli-test-oob-1-slug'), "
                "('acceslibre', 'cli-test-oob-2', 'Lieu Hors Bande Deux', 'lieu hors bande deux', "
                "'cli-test-oob-2-slug')"
            )
        )
        await session.execute(
            text(
                "UPDATE place SET confidence = 0.95, duplicate_of_id = "
                "(SELECT id FROM place WHERE source_id = 'cli-test-oob-1') "
                "WHERE source_id = 'cli-test-oob-2'"
            )
        )
        await session.commit()


def test_duplicates_merge_links_the_candidate_and_removes_the_place_from_search(
    db: None, tmp_path: Path
) -> None:
    path = tmp_path / "acceslibre.csv"
    path.write_text(_FIXTURE, encoding="utf-8")
    _import(path)
    review_id = _place_id("test-3")
    candidate_id = _place_id("test-1")

    result = _cli("duplicates", "merge", str(review_id), "--note", "même médiathèque")

    assert result.exit_code == 0, result.output
    assert f"duplicate merged: {review_id} -> {candidate_id}" in result.output
    row = _places(
        f"SELECT canonical_id, duplicate_of_id, operating_status FROM place WHERE id = {review_id}"
    )
    assert row == [(candidate_id, None, "open")]
    assert ("Mediatheque Test Alpha Annexe",) in _places(
        f"SELECT name FROM place_alias WHERE place_id = {candidate_id}"
    )
    assert _places(
        f"SELECT kept_id, merged_id, actor FROM place_merge_log WHERE merged_id = {review_id}"
    ) == [(candidate_id, review_id, "operator")]
    assert _places(
        f"SELECT decision, actor, candidate_id FROM place_review_decision "
        f"WHERE place_id = {review_id}"
    ) == [("merge", "operator", candidate_id)]

    listed = _cli("duplicates", "list").output
    assert not any(line.startswith(f"{review_id}\t") for line in listed.splitlines())

    names = _search()
    assert "Médiathèque Test Alpha" in names
    assert "Mediatheque Test Alpha Annexe" not in names


def test_duplicates_reject_keeps_both_places_and_records_the_decision(
    db: None, tmp_path: Path
) -> None:
    path = tmp_path / "acceslibre.csv"
    path.write_text(_FIXTURE, encoding="utf-8")
    _import(path)
    review_id = _place_id("test-3")
    candidate_id = _place_id("test-1")

    result = _cli("duplicates", "reject", str(review_id), "--note", "annexe distincte")

    assert result.exit_code == 0, result.output
    assert f"duplicate rejected: {review_id}" in result.output
    row = _places(
        f"SELECT canonical_id, duplicate_of_id, operating_status FROM place WHERE id = {review_id}"
    )
    assert row == [(None, None, "open")]
    aliases = [
        name for (name,) in _places(f"SELECT name FROM place_alias WHERE place_id = {candidate_id}")
    ]
    assert "Mediatheque Test Alpha Annexe" not in aliases
    assert _places(f"SELECT id FROM place_merge_log WHERE merged_id = {review_id}") == []
    assert _places(
        f"SELECT decision, actor, candidate_id, note FROM place_review_decision "
        f"WHERE place_id = {review_id}"
    ) == [("reject", "operator", candidate_id, "annexe distincte")]

    assert _cli("duplicates", "list").output.strip() == ""
    names = _search()
    assert "Médiathèque Test Alpha" in names
    assert "Mediatheque Test Alpha Annexe" in names


def test_duplicates_actions_refuse_a_place_without_a_candidate(db: None, tmp_path: Path) -> None:
    path = tmp_path / "acceslibre.csv"
    path.write_text(_FIXTURE, encoding="utf-8")
    _import(path)
    canonical_id = _place_id("test-1")

    for action in ("merge", "reject"):
        result = _cli("duplicates", action, str(canonical_id))
        assert result.exit_code == 1, result.output
        assert "has no pending duplicate candidate" in result.output


async def _prepare_coverage() -> None:
    async with _TestSessionLocal() as session:
        # One place abroad, and one merged duplicate counted on its canonical row only.
        await session.execute(
            text("UPDATE place SET country_code = 'BE' WHERE source_id = 'cli-test-cov-2'")
        )
        await session.execute(
            text(
                "UPDATE place SET canonical_id = "
                "(SELECT id FROM place WHERE source_id = 'cli-test-cov-1') "
                "WHERE source_id = 'cli-test-cov-5'"
            )
        )
        await session.commit()


def test_coverage_csv_counts_places_by_category_and_country(db: None, tmp_path: Path) -> None:
    path = tmp_path / "coverage.csv"
    path.write_text(_COVERAGE_FIXTURE, encoding="utf-8")
    _import(path)
    asyncio.run(_prepare_coverage())

    result = _cli("coverage", "--format", "csv")

    assert result.exit_code == 0, result.output
    lines = result.output.strip().splitlines()
    assert lines[0] == "category,country,places,with_accessibility,fill_rate"
    by_key = {tuple(line.split(",")[:2]): line.split(",")[2:] for line in lines[1:]}
    assert by_key[("library", "FR")] == ["1", "1", "1.0"]
    assert by_key[("library", "BE")] == ["1", "0", "0.0"]
    assert by_key[("museum", "FR")] == ["1", "1", "1.0"]
    assert by_key[("(unresolved)", "FR")] == ["1", "1", "1.0"]
    assert by_key[("total", "")] == ["4", "3", "0.75"]

    out = tmp_path / "coverage-out.csv"
    written = _cli("coverage", "--format", "csv", "--out", str(out))
    assert written.exit_code == 0, written.output
    assert f"coverage csv: 4 rows -> {out}" in written.output
    assert out.read_text(encoding="utf-8") == result.output


def test_commands_are_noops_on_an_empty_place_table(db: None) -> None:
    asyncio.run(_cleanup())

    listed = _cli("duplicates", "list")
    assert listed.exit_code == 0
    assert listed.output.strip() == ""

    exported = _cli("coverage", "--format", "csv")
    assert exported.exit_code == 0
    if not _places("SELECT id FROM place LIMIT 1"):
        assert exported.output.splitlines()[0] == (
            "category,country,places,with_accessibility,fill_rate"
        )
        assert "no places yet" in exported.output
