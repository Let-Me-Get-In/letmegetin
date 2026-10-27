"""Use case: list active accessibility filters."""

from __future__ import annotations

from letmegetin.domain.referential.entities import AccessibilityFilter
from letmegetin.domain.referential.repositories import FilterRepository


async def list_filters(repository: FilterRepository) -> list[AccessibilityFilter]:
    """Return the active search filters, ordered by position."""
    return await repository.list_active()
