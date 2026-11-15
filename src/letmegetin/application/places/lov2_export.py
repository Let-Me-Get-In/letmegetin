"""The lov2 partner feed: the Phase 14 export with AccesLibre's keys and a mapping sidecar (D-04).

Same seven entries, same manifest, same ``latest.json`` as the ODbL export: the only differences
are the licence predicate (``destination=lov2_partner``), the projected column set and the
``mapping.csv`` sidecar written next to the archive — never inside it.

The projection is a decorator over the export repository, so the writer (*and therefore the
ATTRIBUTION block and the manifest*) can only ever see projected rows.
"""

from __future__ import annotations

import csv
import io
import os
from collections.abc import AsyncIterator, Iterable, Mapping, Sequence
from pathlib import Path
from typing import cast

from letmegetin.application.places.export import ExportReport, export_odbl
from letmegetin.config import settings
from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.acceslibre_map import THEIR_FIELD_FOR_SLUG
from letmegetin.domain.places.export import ExportEventRepository
from letmegetin.domain.places.export_plan import (
    ALIASES_HEADER,
    ExportHeaders,
    ExportPlanRepository,
)
from letmegetin.domain.places.lov2_projection import (
    LOV2_ANSWERS_HEADER,
    LOV2_CATEGORIES_HEADER,
    LOV2_CRITERIA_HEADER,
    LOV2_PLACES_HEADER,
    MAPPING_HEADER,
    MappingRow,
    ProjectedAlias,
    ProjectedAnswer,
    ProjectedCategory,
    ProjectedCriterion,
    ProjectedPlace,
    UnmappableAnswer,
    UnmappablePlace,
    canonical_activites,
    project_alias,
    project_answer,
    project_category,
    project_criterion,
    project_place,
)

PARTNER_DESTINATION = "lov2_partner"
MAPPING_FILE = "mapping.csv"
RULE_FILE = "acceslibre_identifier_rule.csv"
CATEGORIES_FILE = "acceslibre_categories.csv"
MAPPING_DOCUMENT = "acceslibre_mapping.csv"

LOV2_HEADERS = ExportHeaders(
    places=LOV2_PLACES_HEADER,
    categories=LOV2_CATEGORIES_HEADER,
    criteria=LOV2_CRITERIA_HEADER,
    answers=LOV2_ANSWERS_HEADER,
    aliases=ALIASES_HEADER,
)

Unmappable = UnmappablePlace | UnmappableAnswer


def _read_csv(path: Path, header: Sequence[str]) -> list[dict[str, str]]:
    """Reviewed CSV under ``data/referential``: one delimiter, one header, fail closed."""
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            if tuple(reader.fieldnames or ()) != tuple(header):
                raise DomainError(f"{path} needs the header {';'.join(header)}")
            return [{key: (value or "") for key, value in row.items()} for row in reader]
    except OSError as exc:
        raise DomainError(f"{path} is unreadable: {exc}") from exc


def load_identifier_rule(path: Path) -> str:
    """The probe's single recorded rule, the seam every partner key resolves through (D-05).

    :func:`build_lov2_feed` reads it from ``settings.data_dir / acceslibre_identifier_rule.csv``,
    which is also how a test pins a verified rule instead of the committed ``blocked`` default.
    """
    rows = _read_csv(path, ("rule", "detail"))
    rules = {row["rule"].strip() for row in rows if row["rule"].strip()}
    if len(rules) != 1:
        raise DomainError(f"{path} must record exactly one identifier rule, found {sorted(rules)}")
    return rules.pop()


def load_canonical_activites(path: Path) -> dict[str, str]:
    """``category_slug -> activite``, the largest-population row per slug (D-06)."""
    entries: list[tuple[str, str, int]] = []
    for row in _read_csv(path, ("activite", "category_slug", "places")):
        try:
            places = int(row["places"])
        except ValueError as exc:
            raise DomainError(f"{path}: '{row['places']}' is not a place count") from exc
        entries.append((row["activite"], row["category_slug"], places))
    return canonical_activites(entries)


def load_acceslibre_mapping(path: Path) -> list[MappingRow]:
    """The reviewed mapping document; a duplicate or empty row is a gap, never skipped (D-08)."""
    seen: dict[tuple[str, str], MappingRow] = {}
    for row in _read_csv(path, MAPPING_HEADER):
        entity = row["entity"].strip()
        identifier = row["identifier"].strip()
        reason = row["reason"].strip()
        if not entity or not identifier or not reason:
            raise DomainError(f"{path}: a mapping row needs an entity, an identifier and a reason")
        key = (entity, identifier)
        if key in seen:
            raise DomainError(f"{path}: duplicate {entity} row for {identifier}")
        seen[key] = MappingRow(
            entity=entity, identifier=identifier, reason=reason, detail=row["detail"].strip()
        )
    return list(seen.values())


def merge_mapping(static: Iterable[MappingRow], diverted: Iterable[MappingRow]) -> list[MappingRow]:
    """Reviewed rows first; a diverted row never duplicates one, and adds its own count."""
    merged: dict[tuple[str, str, str], MappingRow] = {
        (row.entity, row.identifier or "", row.reason): row for row in static
    }
    for row in diverted:
        key = (row.entity, row.identifier or "", row.reason)
        current = merged.get(key)
        if current is None or not current.detail:
            merged[key] = row
    return sorted(merged.values(), key=lambda row: (row.entity, row.identifier or "", row.reason))


class Lov2ExportRepository:
    """Projects every streamed row into AccesLibre's vocabulary, diverting what it cannot key.

    The five row-returning methods project; every other method (snapshot, version, counts)
    delegates unchanged, so the writer and its manifest read through one repository.
    """

    def __init__(
        self,
        inner: ExportPlanRepository,
        *,
        rule: str,
        activite_for: Mapping[str, str],
        field_for_slug: Mapping[str, str] = THEIR_FIELD_FOR_SLUG,
    ) -> None:
        self._inner = inner
        self._rule = rule
        self._activite_for = activite_for
        self._field_for_slug = field_for_slug
        self._diverted: dict[tuple[str, str, str], tuple[str, int]] = {}

    @property
    def unmappable(self) -> list[MappingRow]:
        """The mapping rows this run produced, one per distinct (entity, identifier, reason)."""
        rows: list[MappingRow] = []
        for (entity, identifier, reason), (detail, count) in sorted(self._diverted.items()):
            suffix = f"{count} rows" if count > 1 else ""
            rows.append(
                MappingRow(
                    entity=entity,
                    identifier=identifier or None,
                    reason=reason,
                    detail=", ".join(part for part in (detail, suffix) if part),
                )
            )
        return rows

    def _divert(self, row: Unmappable) -> None:
        key = (row.entity, row.identifier or "", row.reason)
        current = self._diverted.get(key)
        self._diverted[key] = (current[0], current[1] + 1) if current else (row.detail, 1)

    async def begin_repeatable_read(self) -> None:
        await self._inner.begin_repeatable_read()

    async def referential_version(self) -> int:
        return await self._inner.referential_version()

    async def licence_rules_count(self) -> int:
        return await self._inner.licence_rules_count()

    async def stream_canonical_places(
        self, destination: str, since_seq: int | None = None
    ) -> AsyncIterator[ProjectedPlace]:
        async for row in self._inner.stream_canonical_places(destination, since_seq):
            projected = project_place(row, self._activite_for, self._rule)
            if isinstance(projected, UnmappablePlace):
                self._divert(projected)
            else:
                yield projected

    async def stream_answers(
        self, destination: str, window: tuple[int, int] | None = None
    ) -> AsyncIterator[ProjectedAnswer]:
        async for row in self._inner.stream_answers(destination, window):
            projected = project_answer(row, self._field_for_slug)
            if isinstance(projected, UnmappableAnswer):
                self._divert(projected)
            else:
                yield projected

    async def stream_aliases(self, since_seq: int | None = None) -> AsyncIterator[ProjectedAlias]:
        async for row in self._inner.stream_aliases(since_seq):
            projected = project_alias(row, self._rule)
            if isinstance(projected, UnmappablePlace):
                self._divert(projected)
            else:
                yield projected

    async def list_categories(self) -> list[ProjectedCategory]:
        projected: list[ProjectedCategory] = []
        for row in await self._inner.list_categories():
            category = project_category(row, self._activite_for)
            if category is None:
                self._divert(UnmappablePlace(row.slug, "no_category_inverse", "category"))
            else:
                projected.append(category)
        return projected

    async def list_criteria(self) -> list[ProjectedCriterion]:
        projected: list[ProjectedCriterion] = []
        for row in await self._inner.list_criteria():
            criterion = project_criterion(row, self._field_for_slug)
            if criterion is None:
                self._divert(UnmappableAnswer(row.slug, "not_expressible", "criterion"))
            else:
                projected.append(criterion)
        return projected

    async def place_exclusion_counts(self, destination: str) -> list[tuple[str, str | None, int]]:
        return await self._inner.place_exclusion_counts(destination)

    async def answer_exclusion_counts(self, destination: str) -> list[tuple[str, str | None, int]]:
        return await self._inner.answer_exclusion_counts(destination)

    async def place_withheld_answer_counts(
        self, destination: str
    ) -> list[tuple[str, str | None, int]]:
        return await self._inner.place_withheld_answer_counts(destination)


def _write_mapping(out: Path, rows: Sequence[MappingRow]) -> None:
    """The sidecar next to ``latest.json``: reviewed rows plus this run's diversions."""
    path = out / MAPPING_FILE
    temporary = path.with_name(f".{path.name}.tmp")
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")
    writer.writerow(list(MAPPING_HEADER))
    for row in rows:
        writer.writerow(row.to_csv())
    temporary.write_text(buffer.getvalue(), encoding="utf-8")
    os.replace(temporary, path)


async def build_lov2_feed(
    export: ExportPlanRepository, events: ExportEventRepository, *, out: Path
) -> ExportReport:
    """Write one partner snapshot ZIP plus its ``mapping.csv`` sidecar."""
    data_dir = settings.data_dir
    decorated = Lov2ExportRepository(
        export,
        rule=load_identifier_rule(data_dir / RULE_FILE),
        activite_for=load_canonical_activites(data_dir / CATEGORIES_FILE),
    )
    report = await export_odbl(
        # The writer only needs to_csv() and the provenance fields (CsvRow / SourcedRow), so the
        # decorator's projected rows are the writer's contract even though its type differs.
        cast(ExportPlanRepository, decorated),
        events,
        out=out,
        destination=PARTNER_DESTINATION,
        headers=LOV2_HEADERS,
    )
    _write_mapping(
        out,
        merge_mapping(load_acceslibre_mapping(data_dir / MAPPING_DOCUMENT), decorated.unmappable),
    )
    return report
