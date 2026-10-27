"""Import the Acceslibre open dataset (Etalab 2.0) and deduplicate it on insert.

Acceslibre is the primary French accessibility source; Overture/OSM stay additive through
``place.source``/``source_id`` and ``category_mapping``.

shortcut: local CSV/JSON export only — no live Acceslibre API sync. When scheduled sync is
needed, add an HTTP client that yields the same ``AcceslibreRow`` stream and keep this use
case unchanged (incremental "updated since" belongs to that client).
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from letmegetin.core.utils import slugify
from letmegetin.domain.places.dedup import classify_match, similar_score
from letmegetin.domain.places.entities import Place, make_slug
from letmegetin.domain.places.repositories import (
    CategoryMappingRepository,
    MergeLogRepository,
    PlaceAliasRepository,
    PlaceRepository,
)

SOURCE_ACCESLIBRE = "acceslibre"

# Column aliases seen in the Acceslibre export and its schema documentation.
_COLUMNS: dict[str, tuple[str, ...]] = {
    "source_id": ("id", "id_erp", "source_id"),
    "name": ("nom", "name"),
    "address": ("adresse", "address"),
    "city": ("commune", "ville", "city"),
    "postal_code": ("code_postal", "cp", "postal_code"),
    "lat": ("latitude", "lat"),
    "lng": ("longitude", "lng", "lon"),
    "category": ("categorie", "category", "activite", "activite_principale"),
    "website": ("site_internet", "website", "url"),
    "phone": ("telephone", "phone", "tel"),
}


@dataclass
class AcceslibreRow:
    """One Acceslibre record, normalized to the fields the place aggregate needs."""

    source_id: str
    name: str
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    lat: float | None = None
    lng: float | None = None
    category: str | None = None
    website: str | None = None
    phone: str | None = None


@dataclass
class ImportReport:
    """Outcome of one Acceslibre import."""

    created: int = 0
    linked: int = 0
    review: int = 0
    skipped: int = 0


def _field(record: dict[str, Any], key: str) -> Any:
    for column in _COLUMNS[key]:
        value = record.get(column)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _coordinate(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_row(record: dict[str, Any]) -> AcceslibreRow | None:
    source_id = _field(record, "source_id")
    name = _field(record, "name")
    if not source_id or not name:
        return None
    category = _field(record, "category")
    return AcceslibreRow(
        source_id=str(source_id),
        name=str(name),
        address=_field(record, "address"),
        city=_field(record, "city"),
        postal_code=_field(record, "postal_code"),
        lat=_coordinate(_field(record, "lat")),
        lng=_coordinate(_field(record, "lng")),
        category=str(category) if category else None,
        website=_field(record, "website"),
        phone=_field(record, "phone"),
    )


def _sniff_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t").delimiter
    except csv.Error:
        return ";"


def load_acceslibre_file(path: Path) -> list[AcceslibreRow]:
    """Read a local Acceslibre CSV or JSON export into rows (malformed rows are skipped)."""
    text = path.read_text(encoding="utf-8-sig")
    stripped = text.lstrip()
    if stripped.startswith("[") or stripped.startswith("{"):
        payload = json.loads(stripped)
        records: Iterable[dict[str, Any]] = (
            payload if isinstance(payload, list) else payload.get("results", [])
        )
    else:
        reader = csv.DictReader(text.splitlines(), delimiter=_sniff_delimiter(text[:2048]))
        records = list(reader)
    rows = (_to_row(record) for record in records if isinstance(record, dict))
    return [row for row in rows if row is not None]


async def _resolve_category(mapping: CategoryMappingRepository, category: str | None) -> int | None:
    if not category:
        return None
    return await mapping.resolve_slug(slugify(category))


async def _candidate(places: PlaceRepository, row: AcceslibreRow) -> tuple[Place | None, float]:
    """Best nearby name match and its score; the DB blocks spatially, we score names."""
    if row.lat is None or row.lng is None:
        return None, 0.0
    candidates = await places.get_candidates(row.lat, row.lng, row.name)
    scored = [(hit.place, similar_score(hit.place.name, row.name)) for hit in candidates]
    return max(scored, key=lambda item: item[1], default=(None, 0.0))


async def _import_row(
    places: PlaceRepository,
    mapping: CategoryMappingRepository,
    aliases: PlaceAliasRepository,
    merges: MergeLogRepository,
    row: AcceslibreRow,
    report: ImportReport,
) -> None:
    if await places.get_by_source_id(SOURCE_ACCESLIBRE, row.source_id) is not None:
        report.skipped += 1
        return

    candidate, score = await _candidate(places, row)
    kind = classify_match(score) if candidate is not None else "new"
    place = Place(
        id=0,
        name=row.name,
        slug=make_slug(row.name, SOURCE_ACCESLIBRE, row.source_id),
        source=SOURCE_ACCESLIBRE,
        source_id=row.source_id,
        category_id=await _resolve_category(mapping, row.category),
        address_full=row.address,
        city=row.city,
        postal_code=row.postal_code,
        lat=row.lat,
        lng=row.lng,
        operating_status="duplicate_review" if kind == "review" else "open",
        confidence=round(score, 3) if candidate is not None else None,
        website=row.website,
        phone=row.phone,
        canonical_id=candidate.id if kind == "auto" and candidate is not None else None,
    )
    created = await places.add(place)
    report.created += 1

    if kind == "auto" and candidate is not None:
        report.linked += 1
        await merges.add(candidate.id, created.id, score, actor=SOURCE_ACCESLIBRE)
        if candidate.name.casefold() != created.name.casefold():
            await aliases.add(candidate.id, created.name)
    elif kind == "review":
        report.review += 1


async def import_acceslibre(
    places: PlaceRepository,
    mapping: CategoryMappingRepository,
    aliases: PlaceAliasRepository,
    merges: MergeLogRepository,
    rows: Iterable[AcceslibreRow],
) -> ImportReport:
    """Upsert Acceslibre rows by ``(source, source_id)`` and deduplicate on insert."""
    report = ImportReport()
    for row in rows:
        await _import_row(places, mapping, aliases, merges, row, report)
    return report
