"""Licence catalogue, matrix and source mapping: CSV review, sync counters, audit gate."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from letmegetin.application.referential.licences import (
    audit_licences,
    format_matrix,
    load_licence_destinations,
    load_licences,
    load_source_licences,
    sync_licences,
)
from letmegetin.core.exceptions import DomainError
from letmegetin.domain.referential.entities import Licence, LicenceDestination, SourceLicence
from tests.unit.application.referential.fakes import FakeLicenceRepository


def _csv(path: Path, header: str, rows: str) -> Path:
    path.write_text(f"{header}\n{rows}", encoding="utf-8")
    return path


def test_load_licences_orders_obligations_and_skips_blank_rows(tmp_path: Path) -> None:
    path = _csv(
        tmp_path / "licences.csv",
        "slug;name;url;obligations",
        "odbl;ODbL;https://example.test/odbl;share_alike|attribution\n\nlov2;LO v2;;attribution\n",
    )

    assert load_licences(path) == [
        Licence(
            slug="odbl",
            name="ODbL",
            url="https://example.test/odbl",
            obligations=["share_alike", "attribution"],
        ),
        Licence(slug="lov2", name="LO v2", url=None, obligations=["attribution"]),
    ]


@pytest.mark.parametrize(
    ("rows", "match"),
    [
        ("a;A;;\na;A2;;\n", "duplicate"),
        ("a;;;\n", "names no licence"),
    ],
    ids=["duplicate-slug", "missing-name"],
)
def test_load_licences_rejects_bad_rows(tmp_path: Path, rows: str, match: str) -> None:
    path = _csv(tmp_path / "licences.csv", "slug;name;url;obligations", rows)

    with pytest.raises(DomainError, match=match):
        load_licences(path)


def _destinations(tmp_path: Path, rows: str) -> list[LicenceDestination]:
    path = _csv(
        tmp_path / "licence_destinations.csv", "licence_slug;destination;allowed;note", rows
    )
    return load_licence_destinations(path, {"lov2", "odbl"})


@pytest.mark.parametrize(
    ("rows", "match"),
    [
        ("lov2;carrier_pigeon;true;\n", "carrier_pigeon"),
        ("nope;osm;true;\n", "unknown licence"),
        ("lov2;osm;maybe;\n", "allowed true or false"),
        ("lov2;osm;true;\nlov2;osm;false;\n", "duplicate"),
    ],
    ids=["unknown-destination", "unknown-licence", "not-a-boolean", "duplicate-pair"],
)
def test_load_licence_destinations_rejects_bad_rows(tmp_path: Path, rows: str, match: str) -> None:
    with pytest.raises(DomainError, match=match):
        _destinations(tmp_path, rows)


def test_load_licence_destinations_keeps_the_note(tmp_path: Path) -> None:
    assert _destinations(tmp_path, "odbl;lov2_partner;false;LIC-03\n") == [
        LicenceDestination("odbl", "lov2_partner", False, "LIC-03")
    ]


@pytest.mark.parametrize(
    ("rows", "match"),
    [
        ("acceslibre;nope;2026-10-26\n", "unknown licence"),
        ("acceslibre;lov2;last-tuesday\n", "ISO effective_from"),
        ("acceslibre;lov2;2026-10-26\nacceslibre;odbl;2026-10-26\n", "duplicate"),
    ],
    ids=["unknown-licence", "bad-date", "duplicate-source"],
)
def test_load_source_licences_rejects_bad_rows(tmp_path: Path, rows: str, match: str) -> None:
    path = _csv(tmp_path / "source_licences.csv", "source;licence_slug;effective_from", rows)

    with pytest.raises(DomainError, match=match):
        load_source_licences(path, {"lov2", "odbl"})


def test_load_source_licences_reads_the_effective_date(tmp_path: Path) -> None:
    path = _csv(
        tmp_path / "source_licences.csv",
        "source;licence_slug;effective_from",
        "user;odbl;2026-10-26\n",
    )

    assert load_source_licences(path, {"odbl"}) == [
        SourceLicence("user", "odbl", date(2026, 10, 26))
    ]


async def test_sync_licences_counts_created_then_unchanged() -> None:
    repository = FakeLicenceRepository()
    licences = [Licence(slug="lov2", name="LO v2", obligations=["attribution"])]
    destinations = [LicenceDestination("lov2", "osm", True, None)]
    sources = [SourceLicence("acceslibre", "lov2", date(2026, 10, 26))]

    created = await sync_licences(repository, licences, destinations, sources)

    assert (created.created, created.updated, created.unchanged) == (3, 0, 0)
    assert repository.sources["acceslibre"].licence_slug == "lov2"
    assert await repository.allowed("lov2", "osm") is True

    again = await sync_licences(repository, licences, destinations, sources)

    assert (again.created, again.updated, again.unchanged) == (0, 0, 3)


async def test_sync_licences_counts_a_widened_destination_as_updated() -> None:
    repository = FakeLicenceRepository()
    licences = [Licence(slug="odbl", name="ODbL")]
    await sync_licences(
        repository, licences, [LicenceDestination("odbl", "lov2_partner", False, "LIC-03")], []
    )

    report = await sync_licences(
        repository, licences, [LicenceDestination("odbl", "lov2_partner", True, "widened")], []
    )

    assert (report.created, report.updated, report.unchanged) == (0, 1, 1)
    assert await repository.allowed("odbl", "lov2_partner") is True


async def test_audit_licences_reports_a_missing_destination_row() -> None:
    repository = FakeLicenceRepository([Licence(slug="odbl", name="ODbL")])
    for destination in ("open_export", "osm"):
        await repository.upsert_destination(LicenceDestination("odbl", destination, True, None))

    assert await audit_licences(repository) == [
        "odbl: no matrix rule for destination 'lov2_partner'"
    ]


async def test_audit_licences_reports_a_source_row_outside_the_catalogue() -> None:
    repository = FakeLicenceRepository([Licence(slug="lov2", name="LO v2")])
    for destination in ("open_export", "osm", "lov2_partner"):
        await repository.upsert_destination(LicenceDestination("lov2", destination, True, None))
    await repository.upsert_source_licence(SourceLicence("osm", "odbl", date(2026, 1, 1)))

    assert await audit_licences(repository) == [
        "osm: source licence row names an unknown licence 'odbl'"
    ]


async def test_audit_licences_is_empty_on_a_complete_matrix() -> None:
    repository = FakeLicenceRepository([Licence(slug="lov2", name="LO v2")])
    for destination in ("open_export", "osm", "lov2_partner"):
        await repository.upsert_destination(LicenceDestination("lov2", destination, True, None))

    assert await audit_licences(repository) == []


def test_format_matrix_prints_the_lic03_row_as_denied() -> None:
    printed = format_matrix(
        [
            LicenceDestination("lov2", "lov2_partner", True, None),
            LicenceDestination(
                "odbl", "lov2_partner", False, "OSM-derived never to a lov2 destination (LIC-03)"
            ),
        ]
    )

    rows = printed.splitlines()
    assert rows[0].startswith("lov2_partner\tlov2\tallowed")
    assert rows[1].startswith("lov2_partner\todbl\tdenied")
    assert "LIC-03" in rows[1]
