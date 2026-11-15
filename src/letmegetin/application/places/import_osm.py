"""Import an OpenStreetMap PBF extract, mapped through reviewed OSM tags.

Mirrors the AccesLibre importer: streaming rows, idempotent on ``(source, source_id)``
(D-02), and every category decision comes from reviewed ``category_mapping.osm_tag`` data —
never from a branch in this module (D-05). A POI whose tags match no reviewed tag is skipped
and counted, never guessed (D-06).

shortcut: this slice imports the POI, its mapped category and its raw tag set only. No
accessibility value is written (``_write_source_data`` arrives in 16-02 with the reviewed
``osm_accessibility_tags.csv``) and ``dedup`` is accepted but inert until 16-03.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

from letmegetin.domain.places.entities import Place, make_slug
from letmegetin.domain.places.osm_map import SOURCE, OsmRow
from letmegetin.domain.places.repositories import (
    CategoryMappingRepository,
    MergeLogRepository,
    PlaceAliasRepository,
    PlaceRepository,
)
from letmegetin.domain.referential.repositories import CategoryRepository, CriterionRepository


@dataclass
class OsmImportReport:
    """Outcome of one OSM import."""

    created: int = 0
    linked: int = 0
    review: int = 0
    skipped: int = 0
    resolved: int = 0
    unresolved: int = 0
    # Tag combinations no reviewed category matched, counted per distinct set (D-06).
    unmatched: dict[tuple[str, ...], int] = field(default_factory=dict)


def _tag(tags: Mapping[str, str], key: str) -> str:
    return f"{key}={tags[key]}"


def _matched_tag(tags: Mapping[str, str], osm_tag_for: Mapping[str, int]) -> str | None:
    """First ``key=value`` pair present in the reviewed mapping, in sorted key order."""
    for key in sorted(tags):
        if _tag(tags, key) in osm_tag_for:
            return _tag(tags, key)
    return None


def resolve_osm_category(tags: Mapping[str, str], osm_tag_for: Mapping[str, int]) -> int | None:
    """Category id of the first mapped tag pair, ``None`` when no pair matches (D-06)."""
    tag = _matched_tag(tags, osm_tag_for)
    return None if tag is None else osm_tag_for[tag]


def render_unmatched(report: OsmImportReport, limit: int = 20) -> list[str]:
    """The top unmatched tag combinations, most frequent first: evidence to grow the CSV."""
    ranked = sorted(report.unmatched.items(), key=lambda item: (-item[1], item[0]))
    return [f"  unmatched: {' '.join(tags)}={count}" for tags, count in ranked[:limit]]


async def _import_row(
    places: PlaceRepository,
    mapping: CategoryMappingRepository,
    row: OsmRow,
    report: OsmImportReport,
    osm_tag_for: dict[str, int],
    looked_up: set[str],
    *,
    dry_run: bool,
) -> None:
    if not row.tags:
        # An untagged object is geometry (a way's shared nodes), never a POI.
        return

    # One query per distinct tag string across the whole run, never per POI.
    for key in sorted(row.tags):
        tag = _tag(row.tags, key)
        if tag in looked_up:
            continue
        looked_up.add(tag)
        category_id = await mapping.resolve_osm_tag(tag)
        if category_id is not None:
            osm_tag_for[tag] = category_id

    matched = _matched_tag(row.tags, osm_tag_for)
    category_id = osm_tag_for.get(matched) if matched is not None else None
    if category_id is None:
        # D-06: an unmapped POI is skipped and counted, never guessed into a category.
        report.unresolved += 1
        combination = tuple(sorted(_tag(row.tags, key) for key in row.tags))
        report.unmatched[combination] = report.unmatched.get(combination, 0) + 1
        return
    if not row.name:
        # A mapped object without a name is still not a place (place.name is required).
        return
    report.resolved += 1

    existing = await places.get_by_source_id(SOURCE, row.source_id)
    if existing is not None:
        # D-02: re-running the same extract writes nothing; a newer object version refreshes
        # the OSM identity in place. The name is never rewritten from a re-import.
        if not dry_run and existing.osm_version != row.version:
            existing.category_id = category_id
            existing.source_category = matched
            existing.osm_version = row.version
            existing.osm_tags = row.tags
            existing.retrieved_at = datetime.now(UTC).replace(tzinfo=None)
            await places.update(existing)
        report.skipped += 1
        return

    place = Place(
        id=0,
        name=row.name,
        slug=make_slug(row.name, SOURCE, row.source_id),
        source=SOURCE,
        source_id=row.source_id,
        category_id=category_id,
        source_category=matched,
        lat=row.lat,
        lng=row.lng,
        # The two facts the .osmChange <modify> later needs (BLOCKER 1).
        osm_version=row.version,
        osm_tags=row.tags,
        retrieved_at=datetime.now(UTC).replace(tzinfo=None),
        observed_at=None,
    )
    report.created += 1
    if dry_run:
        return
    await places.add(place)


async def import_osm(
    places: PlaceRepository,
    categories: CategoryRepository,
    mapping: CategoryMappingRepository,
    place_aliases: PlaceAliasRepository,
    merges: MergeLogRepository,
    criteria: CriterionRepository,
    rows: Iterable[OsmRow],
    *,
    dry_run: bool = False,
    dedup: bool = True,
) -> OsmImportReport:
    """Upsert OSM rows by ``(source, source_id)``.

    ``categories``, ``place_aliases``, ``merges``, ``criteria`` and ``dedup`` are the
    contract the 16-02/16-03 slices fill: accessibility mapping, dedup candidate lookup and
    the merge log. They are inert here so the CLI does not change again.
    """
    report = OsmImportReport()
    # Memoised like the AccesLibre importer's label cache: a reviewed tag is resolved once.
    osm_tag_for: dict[str, int] = {}
    looked_up: set[str] = set()
    for row in rows:
        await _import_row(
            places,
            mapping,
            row,
            report,
            osm_tag_for,
            looked_up,
            dry_run=dry_run,
        )
    return report
