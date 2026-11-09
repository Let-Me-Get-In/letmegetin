"""Re-resolve imported places a previous import left without a category.

Filling a gap in ``acceslibre_categories.csv`` used to require re-reading the whole national
export. The raw ``place.source_category`` is persisted for exactly this reason, so the alias
file can be re-applied on its own.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from letmegetin.application.places.category_resolution import resolve_category
from letmegetin.domain.places.repositories import CategoryMappingRepository, PlaceRepository
from letmegetin.domain.referential.repositories import CategoryRepository


@dataclass(frozen=True)
class ReclassifyReport:
    """What one pass resolved, and what is still unmapped."""

    resolved: dict[str, int] = field(default_factory=dict)
    unresolved: list[tuple[str, int]] = field(default_factory=list)
    dry_run: bool = False


async def reclassify_places(
    places: PlaceRepository,
    categories: CategoryRepository,
    mapping: CategoryMappingRepository,
    aliases: Mapping[str, str],
    *,
    dry_run: bool = False,
) -> ReclassifyReport:
    """Re-apply the alias file to the places whose ``source_category`` never resolved."""
    resolved: dict[str, int] = {}
    unresolved: list[tuple[str, int]] = []
    for value, count in await places.unresolved_categories():
        category_id = await resolve_category(aliases, categories, mapping, value)
        if category_id is None:
            unresolved.append((value, count))
            continue
        if not dry_run:
            await places.reassign_category(value, category_id)
        resolved[value] = count
    return ReclassifyReport(resolved=resolved, unresolved=unresolved, dry_run=dry_run)
