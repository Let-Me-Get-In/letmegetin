"""Repository ports for the referential context (implemented in infrastructure)."""

from __future__ import annotations

from typing import Protocol

from letmegetin.domain.referential.entities import (
    AccessibilityFilter,
    Category,
    Criterion,
    OtherInformation,
    VocabularyEntry,
)


class CategoryRepository(Protocol):
    """Read access to place categories."""

    async def list_all(self) -> list[Category]: ...

    async def get_by_slug(self, slug: str) -> Category | None: ...


class CriterionRepository(Protocol):
    """Read access to the accessibility criteria tree."""

    async def list_for_category(self, category_id: int) -> list[Criterion]:
        """Return the applicable criteria plus their ancestors and descendants."""
        ...


class VocabularyRepository(Protocol):
    """Read/write access to the flat criteria vocabulary."""

    async def list_all(self) -> list[VocabularyEntry]: ...

    async def get_by_slug(self, slug: str) -> VocabularyEntry | None: ...

    async def add(self, entry: VocabularyEntry) -> VocabularyEntry: ...

    async def update(self, entry: VocabularyEntry) -> VocabularyEntry: ...


class FilterRepository(Protocol):
    """Read access to search filters."""

    async def list_active(self) -> list[AccessibilityFilter]: ...


class OtherInformationRepository(Protocol):
    """Read access to official labels."""

    async def list_all(self) -> list[OtherInformation]: ...
