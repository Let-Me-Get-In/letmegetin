"""Repository ports for the referential context (implemented in infrastructure)."""

from __future__ import annotations

from typing import Literal, Protocol

from letmegetin.domain.referential.entities import (
    AccessibilityFilter,
    Category,
    CategoryGrid,
    CategoryMapping,
    Criterion,
    OtherInformation,
    VocabularyEntry,
)

MappingState = Literal["include", "exclude", "clear"]


class CategoryRepository(Protocol):
    """Read/write access to place categories."""

    async def list_all(self) -> list[Category]: ...

    async def get_by_slug(self, slug: str) -> Category | None: ...

    async def add(self, category: Category) -> Category: ...

    async def update(self, category: Category) -> Category: ...


class CriterionRepository(Protocol):
    """Read/write access to the accessibility criteria tree."""

    async def list_for_category(self, category_id: int) -> list[Criterion]:
        """Return the applicable set: defaults minus exclusions plus includes,
        with their ancestors and descendants."""
        ...

    async def list_all(self) -> list[Criterion]: ...

    async def get_by_slug(self, slug: str) -> Criterion | None: ...

    async def add(self, criterion: Criterion) -> Criterion: ...

    async def update(self, criterion: Criterion) -> Criterion: ...


class MappingRepository(Protocol):
    """Write access to the category-to-criterion mapping."""

    async def set_state(self, category_id: int, criterion_id: int, state: MappingState) -> None: ...


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


class CategoryGridRepository(Protocol):
    """Precomputed grids plus the global referential version."""

    async def current_version(self) -> int: ...

    async def bump_version(self) -> int: ...

    async def set_grid(
        self, category_id: int, version: int, tree: list[dict[str, object]]
    ) -> None: ...

    async def get_for_slug(self, slug: str) -> CategoryGrid | None: ...


class MappingAdminRepository(Protocol):
    """Write access to the category-to-source vocabulary mapping."""

    async def upsert(self, mapping: CategoryMapping) -> None: ...
