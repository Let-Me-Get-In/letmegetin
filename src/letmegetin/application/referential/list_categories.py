"""Use case: list place categories."""

from __future__ import annotations

from letmegetin.domain.referential.entities import Category
from letmegetin.domain.referential.repositories import CategoryRepository


async def list_categories(repository: CategoryRepository) -> list[Category]:
    """Return every category, ordered by slug."""
    return await repository.list_all()
