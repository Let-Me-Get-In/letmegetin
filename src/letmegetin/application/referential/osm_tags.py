"""The reviewed OSM accessibility mapping, and the audit that keeps it coherent.

``data/referential/osm_accessibility_tags.csv`` is the only source (D-05): one reviewed row per
``(osm_key, osm_value)`` pair, mapping it onto a criterion slug and that criterion's own typed
value — never a free text and never a tag literal in the importer. A pair the review chose not to
map is an absent row and is dropped at runtime (D-06), which is not an error.

The loader fails closed on a malformed *authored* row (wrong header, empty field, duplicate pair).
Legality against the referential is a separate question and needs the criteria: a boolean criterion
accepts ``true``/``false``, an option criterion accepts the slug of one of its own children, and
anything else is a gap the audit names and the importer refuses — a coercion would write an answer
nobody reviewed.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from pathlib import Path

from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.osm_map import AccessibilityMapping
from letmegetin.domain.referential.entities import Category, Criterion

HEADER = ("osm_key", "osm_value", "criterion_slug", "criterion_value")

BOOLEAN_VALUES = frozenset({"true", "false"})


def load_osm_accessibility_tags(path: Path) -> AccessibilityMapping:
    """Read the reviewed ``osm_key;osm_value;criterion_slug;criterion_value`` rows."""
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            if tuple(reader.fieldnames or ()) != HEADER:
                raise DomainError(f"{path} needs the header {';'.join(HEADER)}")
            mapping: dict[tuple[str, str], tuple[str, str]] = {}
            for row in reader:
                if None in row:
                    raise DomainError(f"{path} has a row with more than {len(HEADER)} columns")
                fields = tuple((row.get(key) or "").strip() for key in HEADER)
                if not all(fields):
                    raise DomainError(f"{path} has an incomplete row: {';'.join(fields)}")
                osm_key, osm_value, criterion_slug, criterion_value = fields
                pair = (osm_key, osm_value)
                if pair in mapping:
                    raise DomainError(f"{path} maps '{osm_key}={osm_value}' twice")
                mapping[pair] = (criterion_slug, criterion_value)
            return mapping
    except OSError as exc:
        raise DomainError(f"{path} is unreadable: {exc}") from exc


def _is_legal(criterion: Criterion, value: str, by_slug: Mapping[str, Criterion]) -> bool:
    if criterion.type == "boolean":
        return value in BOOLEAN_VALUES
    if criterion.type == "option":
        option = by_slug.get(value)
        return option is not None and option.parent_id == criterion.id
    return False


def accessibility_gaps(
    criteria: Iterable[Criterion], mapping: Mapping[tuple[str, str], tuple[str, str]]
) -> list[str]:
    """Every reviewed row that names no criterion, or a value illegal for its type."""
    by_slug = {criterion.slug: criterion for criterion in criteria}
    gaps: list[str] = []
    for (osm_key, osm_value), (criterion_slug, value) in sorted(mapping.items()):
        criterion = by_slug.get(criterion_slug)
        if criterion is None:
            gaps.append(f"{osm_key}={osm_value} names unknown criterion '{criterion_slug}'")
        elif not _is_legal(criterion, value, by_slug):
            gaps.append(
                f"{osm_key}={osm_value} maps '{criterion_slug}' to illegal "
                f"{criterion.type} value '{value}'"
            )
    return gaps


def audit_osm_tags(
    categories: Iterable[Category],
    criteria: Iterable[Criterion],
    category_mapping: Mapping[str, str],
    accessibility_mapping: Mapping[tuple[str, str], tuple[str, str]],
) -> list[str]:
    """Gaps in the reviewed OSM data: an ``osm_tag`` naming nothing, an illegal accessibility value.

    ``category_mapping`` is ``osm_tag -> category slug`` as reviewed. The audit reports, it never
    repairs: a gap is loud so a mapping mistake cannot land as a silently mis-categorised place.
    """
    known = {category.slug for category in categories}
    gaps = [
        f"category_mapping osm_tag '{tag}' resolves to no category '{slug}'"
        for tag, slug in sorted(category_mapping.items())
        if slug not in known
    ]
    return gaps + accessibility_gaps(criteria, accessibility_mapping)
