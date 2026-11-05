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
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from letmegetin.application.places.category_resolution import resolve_category
from letmegetin.domain.places.acceslibre_map import accessibility_values
from letmegetin.domain.places.dedup import classify_match, similar_score
from letmegetin.domain.places.entities import Place, PlacePhoto, make_slug
from letmegetin.domain.places.repositories import (
    CategoryMappingRepository,
    MergeLogRepository,
    PlaceAliasRepository,
    PlaceRepository,
)
from letmegetin.domain.referential.repositories import CategoryRepository

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
    accessibility: dict[str, dict[str, object]] = field(default_factory=dict)
    photos: list[PlacePhoto] = field(default_factory=list)


@dataclass
class ImportReport:
    """Outcome of one Acceslibre import."""

    created: int = 0
    linked: int = 0
    review: int = 0
    skipped: int = 0
    resolved: int = 0
    unresolved: dict[str, int] = field(default_factory=dict)


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


def _photos(record: dict[str, Any]) -> list[PlacePhoto]:
    """Parse an export's ``photos`` (JSON list) or single ``photo_url`` column."""
    raw = record.get("photos")
    items: list[Any] = []
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            items = parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            items = [part.strip() for part in raw.split(";") if part.strip()]
    elif isinstance(raw, list):
        items = raw
    single = record.get("photo_url")
    if isinstance(single, str) and single.strip():
        items.append(single.strip())

    photos: list[PlacePhoto] = []
    for item in items:
        if isinstance(item, str) and item.strip():
            photos.append(PlacePhoto(url=item.strip(), credit="Acceslibre", license="Etalab 2.0"))
        elif isinstance(item, dict) and item.get("url"):
            photos.append(
                PlacePhoto(
                    url=str(item["url"]),
                    credit=item.get("credit"),
                    license=item.get("license"),
                )
            )
    return photos


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
        accessibility=accessibility_values(record),
        photos=_photos(record),
    )


def _sniff_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t").delimiter
    except csv.Error:
        return ";"


def iter_acceslibre_rows(path: Path) -> Iterator[AcceslibreRow]:
    """Stream a local Acceslibre CSV export (malformed rows are skipped, never fatal).

    A national export is hundreds of MB, so the CSV branch reads the file handle row by
    row. JSON support is kept for small exports only.
    """
    with path.open(encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(2048)
        if sample.lstrip().startswith(("[", "{")):
            # shortcut: JSON exports are parsed in memory; switch to ijson if one exceeds RAM
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            records: Iterable[dict[str, Any]] = (
                payload if isinstance(payload, list) else payload.get("results", [])
            )
            for record in records:
                if isinstance(record, dict):
                    row = _to_row(record)
                    if row is not None:
                        yield row
            return
        handle.seek(0)
        for record in csv.DictReader(handle, delimiter=_sniff_delimiter(sample)):
            row = _to_row(record)
            if row is not None:
                yield row


def load_acceslibre_file(path: Path) -> list[AcceslibreRow]:
    """Materialise the export (tests and small files only; the CLI streams)."""
    return list(iter_acceslibre_rows(path))


async def _candidate(places: PlaceRepository, row: AcceslibreRow) -> tuple[Place | None, float]:
    """Best nearby name match and its score; the DB blocks spatially, we score names."""
    if row.lat is None or row.lng is None:
        return None, 0.0
    candidates = await places.get_candidates(row.lat, row.lng, row.name)
    scored = [(hit.place, similar_score(hit.place.name, row.name)) for hit in candidates]
    return max(scored, key=lambda item: item[1], default=(None, 0.0))


async def _write_source_data(places: PlaceRepository, place_id: int, row: AcceslibreRow) -> None:
    """Persist the source-owned accessibility values and photos for one place."""
    await places.upsert_accessibility(place_id, row.accessibility)
    await places.upsert_photos(place_id, row.photos)


async def _import_row(
    places: PlaceRepository,
    categories: CategoryRepository,
    mapping: CategoryMappingRepository,
    place_aliases: PlaceAliasRepository,
    merges: MergeLogRepository,
    aliases: Mapping[str, str],
    row: AcceslibreRow,
    report: ImportReport,
    resolved: dict[str, int | None],
    *,
    dry_run: bool,
    dedup: bool,
) -> None:
    # Persisted raw value is capped at the column width so one long label cannot abort the run.
    source_category = (row.category or "").strip()[:120] or None
    label = row.category or ""
    if label not in resolved:
        resolved[label] = await resolve_category(aliases, categories, mapping, row.category)
    category_id = resolved[label]
    if source_category is not None:
        if category_id is None:
            report.unresolved[source_category] = report.unresolved.get(source_category, 0) + 1
        else:
            report.resolved += 1

    existing = await places.get_by_source_id(SOURCE_ACCESLIBRE, row.source_id)
    if existing is not None:
        # Re-import refreshes the source-owned values without touching contributions.
        if not dry_run:
            await _write_source_data(places, existing.id, row)
        report.skipped += 1
        return

    candidate, score = await _candidate(places, row) if dedup else (None, 0.0)
    kind = classify_match(score) if candidate is not None else "new"
    place = Place(
        id=0,
        name=row.name,
        slug=make_slug(row.name, SOURCE_ACCESLIBRE, row.source_id),
        source=SOURCE_ACCESLIBRE,
        source_id=row.source_id,
        category_id=category_id,
        source_category=source_category,
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
        # Persisting the candidate is what turns the review bucket into a query.
        duplicate_of_id=candidate.id if kind == "review" and candidate is not None else None,
    )
    report.created += 1
    if kind == "auto" and candidate is not None:
        report.linked += 1
    elif kind == "review":
        report.review += 1
    if dry_run:
        return

    created = await places.add(place)
    await _write_source_data(places, created.id, row)

    if kind == "auto" and candidate is not None:
        await merges.add(candidate.id, created.id, score, actor=SOURCE_ACCESLIBRE)
        if candidate.name.casefold() != created.name.casefold():
            await place_aliases.add(candidate.id, created.name)


async def import_acceslibre(
    places: PlaceRepository,
    categories: CategoryRepository,
    mapping: CategoryMappingRepository,
    place_aliases: PlaceAliasRepository,
    merges: MergeLogRepository,
    rows: Iterable[AcceslibreRow],
    *,
    aliases: Mapping[str, str] | None = None,
    dry_run: bool = False,
    dedup: bool = True,
) -> ImportReport:
    """Import rows; ``dedup=False`` skips the per-row candidate lookup.

    shortcut: a first national load into an empty table has nothing to compare
    against, yet pays one PostGIS proximity query per row — four hours for 22 %
    of 634 931 places, measured. Turn it off for the initial load and compute
    the duplicates afterwards in one SQL pass; keep the default for incremental
    imports, where the table is already populated.
    """
    """Upsert Acceslibre rows by ``(source, source_id)`` and deduplicate on insert."""
    report = ImportReport()
    # shortcut: category resolution is memoised per label (391 distinct values in
    # the national export). The dedup proximity query below is still per row and
    # is what dominates a 634k-row load; batch it only if that ever runs again.
    resolved: dict[str, int | None] = {}
    for row in rows:
        await _import_row(
            places,
            categories,
            mapping,
            place_aliases,
            merges,
            aliases or {},
            row,
            report,
            resolved,
            dry_run=dry_run,
            dedup=dedup,
        )
    return report
