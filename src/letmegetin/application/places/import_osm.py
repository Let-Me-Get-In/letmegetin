"""Import an OpenStreetMap PBF extract, mapped through reviewed OSM tags.

Mirrors the AccesLibre importer: streaming rows, idempotent on ``(source, source_id)``
(D-02), and every category decision comes from reviewed ``category_mapping.osm_tag`` data —
never from a branch in this module (D-05). A POI whose tags match no reviewed tag is skipped
and counted, never guessed (D-06). Accessibility values come from the reviewed
``osm_accessibility_tags.csv`` through the same rule: a tag pair the review did not map is
dropped, never coerced, and the mapping is validated against the referential before the first
row is read, so a bad row fails the whole run instead of one place.

Duplicates are resolved by the Phase-3 scorer unchanged, against our own database — never an
external API (D-07): the DB blocks spatially at 100 m, the names are scored here, and the
reviewed thresholds decide. An auto match is a *linked* row (``canonical_id``, name kept as an
alias, merge logged), a 0.75-0.90 match is diverted to the review queue, and nothing is ever
deleted or hard-merged (D-08).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

from letmegetin.application.referential.osm_tags import (
    accessibility_gaps,
    load_osm_accessibility_tags,
)
from letmegetin.config import settings
from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.dedup import classify_match, similar_score
from letmegetin.domain.places.entities import Place, make_slug
from letmegetin.domain.places.osm_map import (
    SOURCE,
    AccessibilityMapping,
    OsmRow,
    accessibility_values,
)
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
    return [f"  unmatched: {'|'.join(tags)} = {count}" for tags, count in ranked[:limit]]


async def _write_source_data(
    places: PlaceRepository, place_id: int, values: dict[str, dict[str, object]]
) -> None:
    """Persist the source-owned accessibility values for one place (never a contribution)."""
    await places.upsert_accessibility(
        place_id, values, source=SOURCE, actor=f"importer:{SOURCE}", observed_at=None
    )


async def _candidate(places: PlaceRepository, row: OsmRow) -> tuple[Place | None, float]:
    """Best nearby name match and its score; the DB blocks spatially, we score names."""
    if row.lat is None or row.lng is None or not row.name:
        return None, 0.0
    candidates = await places.get_candidates(row.lat, row.lng, row.name)
    scored = [(hit.place, similar_score(hit.place.name, row.name)) for hit in candidates]
    return max(scored, key=lambda item: item[1], default=(None, 0.0))


async def _import_row(
    places: PlaceRepository,
    mapping: CategoryMappingRepository,
    place_aliases: PlaceAliasRepository,
    merges: MergeLogRepository,
    row: OsmRow,
    report: OsmImportReport,
    osm_tag_for: dict[str, int],
    looked_up: set[str],
    accessibility: AccessibilityMapping,
    *,
    dry_run: bool,
    dedup: bool,
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
    # D-05/D-06: only reviewed tag pairs produce a value; the rest are dropped, not guessed.
    values = accessibility_values(row.tags, accessibility)

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
            await _write_source_data(places, existing.id, values)
        report.skipped += 1
        return

    candidate, score = await _candidate(places, row) if dedup else (None, 0.0)
    kind = classify_match(score) if candidate is not None else "new"
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
        # D-08: a duplicate is a soft link, never a second place and never a deletion.
        operating_status="duplicate_review" if kind == "review" else "open",
        confidence=round(score, 3) if candidate is not None else None,
        canonical_id=candidate.id if kind == "auto" and candidate is not None else None,
        # Persisting the candidate is what turns the review bucket into a query.
        duplicate_of_id=candidate.id if kind == "review" and candidate is not None else None,
        # The two facts the .osmChange <modify> later needs (BLOCKER 1).
        osm_version=row.version,
        osm_tags=row.tags,
        retrieved_at=datetime.now(UTC).replace(tzinfo=None),
        observed_at=None,
    )
    report.created += 1
    if kind == "auto" and candidate is not None:
        report.linked += 1
    elif kind == "review":
        report.review += 1
    if dry_run:
        return
    created = await places.add(place)
    await _write_source_data(places, created.id, values)

    if kind == "auto" and candidate is not None:
        await merges.add(candidate.id, created.id, score, actor=SOURCE)
        if candidate.name.casefold() != created.name.casefold():
            await place_aliases.add(candidate.id, created.name)


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

    ``dedup=False`` skips the per-row candidate lookup: the initial national load has nothing
    to compare against, yet pays one PostGIS proximity query per POI — the same documented
    fast path as the AccesLibre importer. Keep the default for incremental imports.
    """
    accessibility = load_osm_accessibility_tags(settings.data_dir / "osm_accessibility_tags.csv")
    gaps = accessibility_gaps(await criteria.list_all(), accessibility)
    if gaps:
        # Fail closed before the first row: a reviewed row that names nothing is a data bug,
        # never a value to coerce (open question 2).
        raise DomainError("osm accessibility mapping is not coherent:\n" + "\n".join(gaps))

    report = OsmImportReport()
    # Memoised like the AccesLibre importer's label cache: a reviewed tag is resolved once.
    osm_tag_for: dict[str, int] = {}
    looked_up: set[str] = set()
    for row in rows:
        await _import_row(
            places,
            mapping,
            place_aliases,
            merges,
            row,
            report,
            osm_tag_for,
            looked_up,
            accessibility,
            dry_run=dry_run,
            dedup=dedup,
        )
    return report
