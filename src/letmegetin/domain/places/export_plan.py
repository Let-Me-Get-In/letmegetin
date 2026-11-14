"""The ODbL export plan: one frozen row per file, the CSV serialisers and the manifest.

Pure module (no SQLAlchemy, no FastAPI): the repository maps ORM rows to these dataclasses and
the use case streams them through :mod:`csv` into the ZIP (D-01, D-02).

"Origin id" means, per file: places → the pair (source, source_id); answers → the natural key
(place_id, criterion_slug); categories and criteria → the slug. Those are the stable
identifiers EXP-01 promises a partner, independent of our surrogate ids.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import AsyncIterator, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from letmegetin.domain.places.export import _json_value

SCHEMA_VERSION = "1.0"

PLACES_FILE = "places.csv"
CATEGORIES_FILE = "categories.csv"
CRITERIA_FILE = "criteria.csv"
ANSWERS_FILE = "answers.csv"
ALIASES_FILE = "aliases.csv"
ATTRIBUTION_FILE = "ATTRIBUTION.txt"
MANIFEST_FILE = "manifest.json"

MODE_SNAPSHOT = "snapshot"

PLACES_HEADER = (
    "place_id",
    "origin_id",
    "slug",
    "name",
    "category_slug",
    "source_category",
    "address_full",
    "city",
    "postal_code",
    "country_code",
    "lat",
    "lng",
    "operating_status",
    "website",
    "phone",
    "source",
    "source_license",
    "source_url",
    "date",
)
CATEGORIES_HEADER = ("category_id", "slug", "parent_id", "parent_slug", "name", "label")
CRITERIA_HEADER = (
    "criterion_id",
    "slug",
    "parent_id",
    "parent_slug",
    "type",
    "position",
    "handicap_families",
    "label",
    "en17210_ref",
)
ANSWERS_HEADER = (
    "place_id",
    "criterion_slug",
    "value",
    "source",
    "source_license",
    "source_url",
    "date",
)
ALIASES_HEADER = ("alias_id", "canonical_id")

# The formula-injection guard is allow-listed to free text, never blanket (F4): a negative
# longitude or a +phone number must reach the partner unchanged. JSON columns always start
# with "{" so listing them costs nothing and keeps the rule per-column.
FREE_TEXT_COLUMNS: dict[str, frozenset[str]] = {
    PLACES_FILE: frozenset({"name", "address_full", "city", "source_category"}),
    CATEGORIES_FILE: frozenset({"name", "label"}),
    CRITERIA_FILE: frozenset({"label"}),
}
_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _iso(moment: datetime | None) -> str | None:
    """ISO 8601 through the journal's shared converter, so every export date looks the same."""
    return None if moment is None else str(_json_value(moment))


def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


@dataclass(frozen=True, slots=True)
class PlaceRow:
    """One canonical place; ``date`` is the source's claim, else our retrieval (D-06)."""

    place_id: int
    origin_id: str | None
    slug: str
    name: str
    category_slug: str | None
    source_category: str | None
    address_full: str | None
    city: str | None
    postal_code: str | None
    country_code: str
    lat: float | None
    lng: float | None
    operating_status: str
    website: str | None
    phone: str | None
    source: str
    source_license: str | None
    source_url: str | None
    date: datetime | None

    def to_csv(self) -> tuple[object, ...]:
        return (
            self.place_id,
            self.origin_id,
            self.slug,
            self.name,
            self.category_slug,
            self.source_category,
            self.address_full,
            self.city,
            self.postal_code,
            self.country_code,
            self.lat,
            self.lng,
            self.operating_status,
            self.website,
            self.phone,
            self.source,
            self.source_license,
            self.source_url,
            _iso(self.date),
        )


@dataclass(frozen=True, slots=True)
class CategoryRow:
    """One category, its parent resolved to a slug so the tree survives a re-import."""

    category_id: int
    slug: str
    parent_id: int | None
    parent_slug: str | None
    name: str
    label: dict[str, object]

    def to_csv(self) -> tuple[object, ...]:
        return (
            self.category_id,
            self.slug,
            self.parent_id,
            self.parent_slug,
            self.name,
            _json_text(self.label),
        )


@dataclass(frozen=True, slots=True)
class CriterionRow:
    """One criterion; ``handicap_families`` stays a JSON list and label a JSON object."""

    criterion_id: int
    slug: str
    parent_id: int | None
    parent_slug: str | None
    type: str
    position: int
    handicap_families: list[str]
    label: dict[str, object]
    en17210_ref: str | None

    def to_csv(self) -> tuple[object, ...]:
        return (
            self.criterion_id,
            self.slug,
            self.parent_id,
            self.parent_slug,
            self.type,
            self.position,
            _json_text(self.handicap_families),
            _json_text(self.label),
            self.en17210_ref,
        )


@dataclass(frozen=True, slots=True)
class AnswerRow:
    """One winning answer keyed by (effective canonical place_id, criterion_slug).

    ``date`` is ``observed_at`` else ``recorded_at`` — an answer has no ``retrieved_at``
    (D-06, I2). ``source_url`` is always empty: an answer carries no page of its own.
    """

    place_id: int
    criterion_slug: str
    value: dict[str, object]
    source: str
    source_license: str | None
    date: datetime | None

    def to_csv(self) -> tuple[object, ...]:
        return (
            self.place_id,
            self.criterion_slug,
            _json_text(self.value),
            self.source,
            self.source_license,
            "",
            _iso(self.date),
        )


@dataclass(frozen=True, slots=True)
class AliasRow:
    """A merged place and the canonical place its identity now resolves to (D-04)."""

    alias_id: int
    canonical_id: int

    def to_csv(self) -> tuple[object, ...]:
        return (self.alias_id, self.canonical_id)


ExportRow = PlaceRow | CategoryRow | CriterionRow | AnswerRow | AliasRow


def guard_indexes(header: Sequence[str], file: str) -> list[int]:
    """The column positions the formula guard applies to, computed once per file (F4)."""
    free_text = FREE_TEXT_COLUMNS.get(file, frozenset())
    return [index for index, name in enumerate(header) if name in free_text]


def _guard_csv_cell(value: object) -> object:
    """Prefix a leading quote onto a free-text cell a spreadsheet would run as a formula."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def guarded_cells(row: ExportRow, indexes: Sequence[int]) -> list[object]:
    """The row's cells with the free-text columns guarded; every other column untouched."""
    cells = list(row.to_csv())
    for index in indexes:
        cells[index] = _guard_csv_cell(cells[index])
    return cells


def serialise_rows(header: Sequence[str], rows: Iterable[ExportRow], file: str) -> str:
    """RFC 4180 CSV text, UTF-8, header row, no BOM — the exact shape D-02 promises."""
    indexes = guard_indexes(header, file)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(list(header))
    for row in rows:
        writer.writerow(guarded_cells(row, indexes))
    return buffer.getvalue()


Counts = Sequence[tuple[str, str | None, int]]


def _count_rows(counts: Counts) -> list[dict[str, object]]:
    return [
        {"source": source, "licence": licence, "count": count} for source, licence, count in counts
    ]


def build_manifest(
    *,
    generated_at: datetime,
    referential_version: int,
    files: Mapping[str, int],
    excluded_places: Counts,
    excluded_answers: Counts,
    place_withheld_answers: Counts,
    attribution: str,
    mode: str = MODE_SNAPSHOT,
    from_seq: int | None = None,
    to_seq: int | None = None,
) -> dict[str, object]:
    """The manifest dict (D-02, W3): what the ZIP holds and what the licence kept out of it.

    A delta or catch-up also records ``mode``, ``from_seq`` and ``to_seq`` so a partner can
    apply the windows in order (W5); a snapshot carries none of the three.
    """
    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _iso(generated_at),
        "referential_version": referential_version,
        "files": dict(files),
        "excluded_places": _count_rows(excluded_places),
        "excluded_answers": _count_rows(excluded_answers),
        "place_withheld_answers": _count_rows(place_withheld_answers),
        "attribution": attribution,
        "attribution_ref": ATTRIBUTION_FILE,
    }
    if mode != MODE_SNAPSHOT:
        manifest["mode"] = mode
        manifest["from_seq"] = from_seq
        manifest["to_seq"] = to_seq
    return manifest


def answer_precedence(
    *, canonical_id: int, place_id: int, recorded_at: datetime, criterion_id: int
) -> tuple[int, float, int, int]:
    """Sort key of the deterministic winner order (W4); the SQL ``ORDER BY`` is its twin.

    The canonical place's own answer wins, then the newest ``recorded_at``, then the highest
    ids — so a replay picks the same row every time, in a snapshot and in a delta alike.
    """
    return (
        0 if place_id == canonical_id else 1,
        -recorded_at.timestamp(),
        -place_id,
        -criterion_id,
    )


class ExportPlanRepository(Protocol):
    """The bulk read an export needs; streamed, never materialised (635k places / 1.7M answers)."""

    async def begin_repeatable_read(self) -> None:
        """Pin one REPEATABLE READ snapshot before the boundary is read (B5)."""
        ...

    async def referential_version(self) -> int: ...

    async def licence_rules_count(self) -> int:
        """Rows in the reviewed matrix; zero means the licence data was never loaded (D-15)."""
        ...

    def stream_canonical_places(
        self, destination: str, since_seq: int | None = None
    ) -> AsyncIterator[PlaceRow]: ...

    def stream_answers(
        self, destination: str, window: tuple[int, int] | None = None
    ) -> AsyncIterator[AnswerRow]: ...

    def stream_aliases(self, since_seq: int | None = None) -> AsyncIterator[AliasRow]: ...

    async def list_categories(self) -> list[CategoryRow]: ...

    async def list_criteria(self) -> list[CriterionRow]: ...

    async def place_exclusion_counts(self, destination: str) -> list[tuple[str, str | None, int]]:
        """Canonical places the matrix withholds, per (source, licence)."""
        ...

    async def answer_exclusion_counts(self, destination: str) -> list[tuple[str, str | None, int]]:
        """Withheld answers plus ranking losers, per (source, licence) (D-03, D-04)."""
        ...

    async def place_withheld_answer_counts(
        self, destination: str
    ) -> list[tuple[str, str | None, int]]:
        """Answers whose canonical place is withheld at place level (W3)."""
        ...
