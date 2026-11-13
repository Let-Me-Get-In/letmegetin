"""Licence rules as reviewed data: catalogue, redistribution matrix and source mapping.

``data/referential/licences.csv``, ``licence_destinations.csv`` and ``source_licences.csv``
are the only source of truth (LIC-05): adding a destination, widening a rule or mapping a
source to a licence is a git-reviewed row, never a branch here.
"""

from __future__ import annotations

import csv
from collections.abc import Collection, Iterator, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from letmegetin.core.exceptions import DomainError
from letmegetin.domain.referential.entities import Licence, LicenceDestination, SourceLicence
from letmegetin.domain.referential.repositories import LicenceRepository

# The closed set a licence may leave towards (D-06); a CheckConstraint backs it in the DB.
LICENCE_DESTINATIONS: tuple[str, ...] = ("open_export", "osm", "lov2_partner")

_TRUE = {"true", "yes", "1"}
_FALSE = {"false", "no", "0"}


@dataclass
class LicenceReport:
    """Rows written by one ``sync_licences`` run, across the three tables."""

    created: int = 0
    updated: int = 0
    unchanged: int = 0


def _read(path: Path) -> Iterator[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle, delimiter=";")


def load_licences(path: Path) -> list[Licence]:
    """Read ``slug;name;url;obligations`` rows where obligations are ``|``-separated."""
    licences: list[Licence] = []
    seen: set[str] = set()
    for row in _read(path):
        slug = (row.get("slug") or "").strip()
        if not slug:
            continue
        if slug in seen:
            raise DomainError(f"duplicate licence row for '{slug}'")
        seen.add(slug)
        name = (row.get("name") or "").strip()
        if not name:
            raise DomainError(f"licence row '{slug}' names no licence")
        obligations = [item.strip() for item in (row.get("obligations") or "").split("|")]
        licences.append(
            Licence(
                slug=slug,
                name=name,
                url=(row.get("url") or "").strip() or None,
                obligations=[item for item in obligations if item],
            )
        )
    return licences


def load_licence_destinations(
    path: Path, licence_slugs: Collection[str]
) -> list[LicenceDestination]:
    """Read ``licence_slug;destination;allowed;note`` rows against the catalogue."""
    destinations: list[LicenceDestination] = []
    seen: set[tuple[str, str]] = set()
    for row in _read(path):
        licence_slug = (row.get("licence_slug") or "").strip()
        destination = (row.get("destination") or "").strip()
        if not licence_slug and not destination:
            continue
        if licence_slug not in licence_slugs:
            raise DomainError(f"licence destination row names unknown licence '{licence_slug}'")
        if destination not in LICENCE_DESTINATIONS:
            allowed = ", ".join(LICENCE_DESTINATIONS)
            raise DomainError(
                f"'{licence_slug}' has unsupported destination '{destination}' (allowed: {allowed})"
            )
        if (licence_slug, destination) in seen:
            raise DomainError(
                f"duplicate licence destination row for '{licence_slug}' -> '{destination}'"
            )
        seen.add((licence_slug, destination))
        destinations.append(
            LicenceDestination(
                licence_slug=licence_slug,
                destination=destination,
                allowed=_allowed(licence_slug, destination, row.get("allowed")),
                note=(row.get("note") or "").strip() or None,
            )
        )
    return destinations


def _allowed(licence_slug: str, destination: str, raw: str | None) -> bool:
    value = (raw or "").strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise DomainError(
        f"licence destination '{licence_slug}' -> '{destination}' needs allowed true or false"
    )


def load_source_licences(path: Path, licence_slugs: Collection[str]) -> list[SourceLicence]:
    """Read ``source;licence_slug;effective_from`` rows against the catalogue."""
    sources: list[SourceLicence] = []
    seen: set[str] = set()
    for row in _read(path):
        source = (row.get("source") or "").strip()
        if not source:
            continue
        licence_slug = (row.get("licence_slug") or "").strip()
        if licence_slug not in licence_slugs:
            raise DomainError(
                f"source licence row for '{source}' names unknown licence '{licence_slug}'"
            )
        if source in seen:
            raise DomainError(f"duplicate source licence row for '{source}'")
        seen.add(source)
        raw_date = (row.get("effective_from") or "").strip()
        try:
            effective_from = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise DomainError(
                f"source licence row for '{source}' needs an ISO effective_from date"
            ) from exc
        sources.append(SourceLicence(source, licence_slug, effective_from))
    return sources


async def sync_licences(
    repository: LicenceRepository,
    licences: Sequence[Licence],
    destinations: Sequence[LicenceDestination],
    source_licences: Sequence[SourceLicence],
) -> LicenceReport:
    """Upsert the catalogue, then its matrix, then the source mapping — through the port.

    Order matters: ``licence_destination`` and ``source_licence`` carry a foreign key to
    ``licence``, so the catalogue is written first. Every write is an upsert, so a re-run
    leaves a reviewed database untouched.
    """
    report = LicenceReport()
    current_licences = {item.slug: item for item in await repository.list_licences()}
    for licence in licences:
        _tally(report, current_licences.get(licence.slug), licence)
        await repository.upsert_licence(licence)

    current_destinations = {
        (row.licence_slug, row.destination): row for row in await repository.list_destinations()
    }
    for destination in destinations:
        _tally(
            report,
            current_destinations.get((destination.licence_slug, destination.destination)),
            destination,
        )
        await repository.upsert_destination(destination)

    current_sources = {row.source: row for row in await repository.list_source_licences()}
    for source in source_licences:
        _tally(report, current_sources.get(source.source), source)
        await repository.upsert_source_licence(source)
    return report


def _tally(report: LicenceReport, existing: object | None, row: object) -> None:
    """Count a row as created, unchanged or updated before it is upserted."""
    if existing is None:
        report.created += 1
    elif existing == row:
        report.unchanged += 1
    else:
        report.updated += 1


async def audit_licences(repository: LicenceRepository) -> list[str]:
    """Return every gap an operator must fix before the matrix may be trusted (D-08).

    One line per catalogue licence with no reviewed row for a destination, and one per
    matrix or source row naming a licence absent from the catalogue. The caller exits 1
    when the list is non-empty, so an erroneous review never widens the rule silently.
    """
    catalogue = {item.slug for item in await repository.list_licences()}
    issues: list[str] = []
    covered: dict[str, set[str]] = {}
    for row in await repository.list_destinations():
        if row.licence_slug not in catalogue:
            issues.append(
                f"{row.licence_slug}: destination row '{row.destination}' names an unknown licence"
            )
            continue
        covered.setdefault(row.licence_slug, set()).add(row.destination)
    for slug in sorted(catalogue):
        for destination in LICENCE_DESTINATIONS:
            if destination not in covered.get(slug, set()):
                issues.append(f"{slug}: no matrix rule for destination '{destination}'")
    for source_row in await repository.list_source_licences():
        if source_row.licence_slug not in catalogue:
            issues.append(
                f"{source_row.source}: source licence row names an unknown licence "
                f"'{source_row.licence_slug}'"
            )
    return issues


def format_matrix(destinations: Sequence[LicenceDestination]) -> str:
    """Render the matrix grouped by destination: ``destination	licence	verdict	note``."""
    if not destinations:
        return "licences matrix: empty"
    rows = sorted(destinations, key=lambda row: (row.destination, row.licence_slug))
    return "\n".join(
        f"{row.destination}\t{row.licence_slug}\t"
        f"{'allowed' if row.allowed else 'denied'}\t{row.note or ''}".rstrip()
        for row in rows
    )
