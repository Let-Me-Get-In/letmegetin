"""Repository ports for the referential context (implemented in infrastructure)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, Protocol

from letmegetin.domain.referential.entities import (
    AccessibilityFilter,
    Category,
    CategoryGrid,
    CategoryMapping,
    Criterion,
    Licence,
    LicenceDestination,
    OtherInformation,
    SourceLicence,
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
    """Read/write access to search filters."""

    async def list_all(self) -> list[AccessibilityFilter]: ...

    async def list_active(self) -> list[AccessibilityFilter]: ...

    async def update_families(self, filter_id: int, families: list[str]) -> None: ...


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

    async def get_for_slugs(self, slugs: Sequence[str]) -> dict[str, CategoryGrid]:
        """The grids of several categories in ONE query, keyed by category slug."""
        ...


class MappingAdminRepository(Protocol):
    """Write access to the category-to-source vocabulary mapping."""

    async def upsert(self, mapping: CategoryMapping) -> None: ...


class LicenceRepository(Protocol):
    """Read/write access to the reviewed licence catalogue, its matrix and the source mapping."""

    async def get_by_slug(self, slug: str) -> Licence | None: ...

    async def list_licences(self) -> list[Licence]: ...

    async def list_destinations(self, licence_slug: str | None = None) -> list[LicenceDestination]:
        """Every matrix row, or the rows of one licence when a slug is given."""
        ...

    async def list_source_licences(self) -> list[SourceLicence]: ...

    async def allowed(self, licence_slug: str, destination: str) -> bool:
        """Fail closed: an absent pair, or an unknown licence, is refused (D-15)."""
        ...

    async def upsert_licence(self, licence: Licence) -> None: ...

    async def upsert_destination(self, row: LicenceDestination) -> None: ...

    async def upsert_source_licence(self, row: SourceLicence) -> None: ...

    async def redistributable_place_ids(self, destination: str) -> list[int]:
        """Bulk twin of ``can_redistribute``: the places allowed to leave (D-13)."""
        ...

    async def exclusion_counts(self, destination: str) -> list[tuple[str, str | None, int]]:
        """Counts, per ``(source, licence)``, of the places a destination leaves out (D-14)."""
        ...

    async def excluded_ids(self, destination: str) -> list[tuple[int, str | None]]:
        """The place ids a destination leaves out, with the licence that kept them out (D-14)."""
        ...
