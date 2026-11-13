"""Functional: the domain predicate and its SQL twin agree, and the manifest counts (D-13/14/15).

The matrix comes from the real database (loaded by ``admin licences sync``, i.e. the
reviewed CSV), never from a literal here: this file proves the rule is data.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import text
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.domain.places.licence import DESTINATIONS, can_redistribute
from letmegetin.infrastructure.persistence.licence_repositories import SqlAlchemyLicenceRepository
from tests.db import SessionLocal, execute, require_database, run

_SLUG_PREFIX = "test-p12r"
_UNKNOWN_LICENCE = "ghost-licence"


def _source(key: str) -> str:
    """A source unique to this test, so the manifest counts are exact."""
    return f"{_SLUG_PREFIX}-{key}"


async def _matrix() -> dict[tuple[str, str], bool]:
    async with SessionLocal() as session:
        destinations = await SqlAlchemyLicenceRepository(session).list_destinations()
    return {(row.licence_slug, row.destination): row.allowed for row in destinations}


async def _allowed(licence: str, destination: str) -> bool:
    async with SessionLocal() as session:
        return await SqlAlchemyLicenceRepository(session).allowed(licence, destination)


async def _redistributable(destination: str) -> list[int]:
    async with SessionLocal() as session:
        return await SqlAlchemyLicenceRepository(session).redistributable_place_ids(destination)


async def _counts(destination: str) -> list[tuple[str, str | None, int]]:
    async with SessionLocal() as session:
        return await SqlAlchemyLicenceRepository(session).exclusion_counts(destination)


async def _excluded(destination: str) -> list[tuple[int, str | None]]:
    async with SessionLocal() as session:
        return await SqlAlchemyLicenceRepository(session).excluded_ids(destination)


async def _seed(matrix: dict[tuple[str, str], bool]) -> dict[str | None, int]:
    """One place per matrix licence, plus the two fail-closed cases (D-15)."""
    keys: list[str | None] = sorted({licence for licence, _ in matrix}) + [None, _UNKNOWN_LICENCE]
    ids: dict[str | None, int] = {}
    async with SessionLocal() as session:
        for key in keys:
            licence = None if key is None else key
            place_id = await session.scalar(
                text(
                    "INSERT INTO place (source, name, name_normalized, slug, source_license) "
                    "VALUES (:source, :name, :name, :slug, :licence) RETURNING id"
                ),
                {
                    "source": _source(licence or "none"),
                    "name": f"Redistribution {licence or 'none'}",
                    "slug": f"{_SLUG_PREFIX}-{licence or 'none'}",
                    "licence": licence,
                },
            )
            ids[key] = int(place_id)
        await session.commit()
    return ids


@pytest.fixture
def places(test_sessions: None) -> Iterator[dict[str | None, int]]:
    require_database("licence", "licence_destination", "place")
    synced = CliRunner().invoke(admin.app, ["licences", "sync"])
    assert synced.exit_code == 0, synced.output

    execute("DELETE FROM place WHERE slug LIKE :pattern", {"pattern": f"{_SLUG_PREFIX}-%"})
    ids = run(_seed(run(_matrix())))
    yield ids
    execute("DELETE FROM place WHERE slug LIKE :pattern", {"pattern": f"{_SLUG_PREFIX}-%"})


def test_the_sql_twin_agrees_with_the_domain_predicate_on_every_matrix_row(
    places: dict[str | None, int],
) -> None:
    matrix = run(_matrix())
    assert matrix, "the reviewed matrix did not load"

    for (licence, destination), allowed in matrix.items():
        assert run(_allowed(licence, destination)) is allowed
        assert can_redistribute(licence, destination, matrix) is allowed
        assert (places[licence] in set(run(_redistributable(destination)))) is allowed


def test_the_lic03_row_keeps_odbl_rows_out_of_a_lov2_destination(
    places: dict[str | None, int],
) -> None:
    assert can_redistribute("odbl", "lov2_partner", run(_matrix())) is False
    assert places["odbl"] not in set(run(_redistributable("lov2_partner")))
    assert places["lov2"] in set(run(_redistributable("lov2_partner")))


@pytest.mark.parametrize("destination", DESTINATIONS)
def test_a_null_or_unknown_licence_matches_no_destination(
    places: dict[str | None, int], destination: str
) -> None:
    allowed = set(run(_redistributable(destination)))
    assert places[None] not in allowed
    assert places[_UNKNOWN_LICENCE] not in allowed


def test_the_manifest_counts_excluded_rows_per_source_and_licence(
    places: dict[str | None, int],
) -> None:
    counts = {(source, licence): count for source, licence, count in run(_counts("lov2_partner"))}

    assert counts[(_source("odbl"), "odbl")] == 1
    assert counts[(_source("none"), None)] == 1
    assert counts[(_source(_UNKNOWN_LICENCE), _UNKNOWN_LICENCE)] == 1
    assert (_source("lov2"), "lov2") not in counts

    excluded = dict(run(_excluded("lov2_partner")))
    assert excluded[places["odbl"]] == "odbl"
    assert excluded[places[None]] is None
    assert places["lov2"] not in excluded


def test_the_operator_lists_the_excluded_ids_for_a_destination(
    places: dict[str | None, int],
) -> None:
    runner = CliRunner()

    listed = runner.invoke(
        admin.app, ["licences", "excluded", "--destination", "lov2_partner", "--verbose"]
    )
    assert listed.exit_code == 0, listed.output
    assert f"place {places['odbl']}" in listed.output
    assert f"place {places[None]}\t(no licence)" in listed.output
    assert f"place {places['lov2']}" not in listed.output

    counted = runner.invoke(admin.app, ["licences", "excluded", "--destination", "lov2_partner"])
    assert counted.exit_code == 0, counted.output
    assert "excluded=" in counted.output
    assert "place " not in counted.output

    refused = runner.invoke(admin.app, ["licences", "excluded", "--destination", "nowhere"])
    assert refused.exit_code == 1
    assert "unknown destination 'nowhere'" in refused.output
