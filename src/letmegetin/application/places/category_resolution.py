"""Resolve an Acceslibre activity label to one of our categories, auditably.

The alias CSV (``data/referential/acceslibre_categories.csv``) is the only place the
source vocabulary mapping lives; this module loads it and applies it in a fixed order so
the same input always lands on the same grid.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path

from letmegetin.core.exceptions import DomainError
from letmegetin.core.utils import slugify
from letmegetin.domain.places.repositories import CategoryMappingRepository
from letmegetin.domain.referential.repositories import CategoryRepository


def load_category_aliases(path: Path) -> dict[str, str]:
    """Read ``activite;category_slug[;places]`` into ``slugified label -> category slug``.

    Rows with an empty ``category_slug`` are the deliberately unmapped gaps of the export
    (they stay visible in ``import report``) and are skipped.
    """
    aliases: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            source = (row.get("activite") or row.get("source_value") or "").strip()
            target = (row.get("category_slug") or "").strip()
            if not target:
                continue
            if not source:
                raise DomainError(f"category aliases: empty source value for '{target}'")
            key = slugify(source)
            if key in aliases:
                raise DomainError(f"category aliases: duplicate source value '{source}'")
            aliases[key] = target
    return aliases


async def resolve_category(
    aliases: Mapping[str, str],
    categories: CategoryRepository,
    mapping: CategoryMappingRepository,
    value: str | None,
) -> int | None:
    """Alias first, then an exact category slug, then ``category_mapping``.

    The exact-slug lookup must come before ``resolve_slug``: the mapping has ambiguous
    buckets (``restaurant`` maps to both ``restaurant`` and ``fast_food_restaurant``), so
    the category's own slug is the authoritative answer when it exists.
    """
    if not value or not value.strip():
        return None
    slug = slugify(value)
    target = aliases.get(slug, slug)
    exact = await categories.get_by_slug(target)
    if exact is not None:
        return exact.id
    return await mapping.resolve_slug(target)
