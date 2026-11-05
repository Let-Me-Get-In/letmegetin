"""Assign the four handicap families to criteria and filters from a reviewed CSV.

``data/referential/families.csv`` is the only source: an operator reviews the family
of every base criterion and filter in the diff instead of in branch logic.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from pathlib import Path

from letmegetin.core.exceptions import DomainError
from letmegetin.domain.referential.entities import HANDICAP_FAMILIES, Criterion
from letmegetin.domain.referential.repositories import CriterionRepository, FilterRepository


@dataclass
class FamiliesReport:
    """Rows written by one ``apply_families`` run."""

    criteria_updated: int = 0
    filters_updated: int = 0
    inherited: int = 0
    unchanged: int = 0


def _validated(slug: str, families: list[str]) -> list[str]:
    unknown = [family for family in families if family not in HANDICAP_FAMILIES]
    if unknown:
        allowed = ", ".join(HANDICAP_FAMILIES)
        raise DomainError(
            f"'{slug}' has unsupported handicap family '{unknown[0]}' (allowed: {allowed})"
        )
    return [family for family in HANDICAP_FAMILIES if family in families]


def load_families(path: Path) -> dict[str, list[str]]:
    """Read ``slug;families`` rows where families are ``|``-separated."""
    assignments: dict[str, list[str]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            slug = (row.get("slug") or "").strip()
            if not slug:
                continue
            if slug in assignments:
                raise DomainError(f"duplicate families row for '{slug}'")
            families = [name.strip() for name in (row.get("families") or "").split("|")]
            if not any(families):
                raise DomainError(f"families row '{slug}' names no handicap family")
            assignments[slug] = _validated(slug, [name for name in families if name])
    return assignments


async def apply_families(
    criteria: CriterionRepository,
    filters: FilterRepository,
    assignments: dict[str, list[str]],
    *,
    overwrite: bool = False,
) -> FamiliesReport:
    """Write explicit rows, then let options inherit and groups union their children."""
    report = FamiliesReport()
    all_criteria = await criteria.list_all()
    all_filters = await filters.list_all()
    criteria_by_slug = {item.slug: item for item in all_criteria}
    filters_by_slug = {item.slug: item for item in all_filters}

    unknown = [
        slug for slug in assignments if slug not in criteria_by_slug and slug not in filters_by_slug
    ]
    if unknown:
        raise DomainError(f"families.csv names unknown slug '{unknown[0]}'")

    for slug, families in assignments.items():
        criterion = criteria_by_slug.get(slug)
        if criterion is not None:
            if (criterion.handicap_families and not overwrite) or (
                criterion.handicap_families == families
            ):
                report.unchanged += 1
                continue
            await criteria.update(replace(criterion, handicap_families=families))
            criterion.handicap_families = families
            report.criteria_updated += 1
            continue
        item = filters_by_slug[slug]
        if (item.handicap_families and not overwrite) or (item.handicap_families == families):
            report.unchanged += 1
            continue
        await filters.update_families(item.id, families)
        item.handicap_families = families
        report.filters_updated += 1

    await _fill_inherited(criteria, all_criteria, report)
    return report


async def _fill_inherited(
    criteria: CriterionRepository, all_criteria: list[Criterion], report: FamiliesReport
) -> None:
    by_id = {item.id: item for item in all_criteria}

    async def inherit(criterion: Criterion, seen: frozenset[int] = frozenset()) -> list[str]:
        if criterion.handicap_families or criterion.parent_id is None:
            return criterion.handicap_families
        if criterion.id in seen:
            raise DomainError(f"criterion '{criterion.slug}' has a cyclic parent chain")
        parent = by_id.get(criterion.parent_id)
        if parent is None:
            return []
        families = await inherit(parent, seen | {criterion.id})
        if families:
            await criteria.update(replace(criterion, handicap_families=families))
            criterion.handicap_families = list(families)
            report.inherited += 1
        return criterion.handicap_families

    for criterion in all_criteria:
        await inherit(criterion)

    children: dict[int, list[Criterion]] = {}
    for criterion in all_criteria:
        if criterion.parent_id is not None:
            children.setdefault(criterion.parent_id, []).append(criterion)

    for criterion in all_criteria:
        direct = children.get(criterion.id, [])
        if not direct or criterion.handicap_families:
            continue
        union = {family for child in direct for family in child.handicap_families}
        families: list[str] = [family for family in HANDICAP_FAMILIES if family in union]
        if families:
            await criteria.update(replace(criterion, handicap_families=families))
            criterion.handicap_families = families
            report.inherited += 1


async def audit_families(criteria: CriterionRepository, filters: FilterRepository) -> list[str]:
    """Return the slugs that carry no facility family, criteria first then filters."""
    missing_criteria = sorted(
        item.slug for item in await criteria.list_all() if not item.handicap_families
    )
    missing_filters = sorted(
        item.slug for item in await filters.list_all() if not item.handicap_families
    )
    return missing_criteria + missing_filters
