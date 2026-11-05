"""Repository ports for the places context (implemented in infrastructure)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from letmegetin.domain.places.entities import (
    HandicapFamily,
    PendingDuplicate,
    Place,
    PlaceAccessibility,
    PlaceHit,
    PlacePhoto,
    Review,
    ReviewDecision,
)

DEFAULT_CANDIDATE_RADIUS = 100.0


class PlaceRepository(Protocol):
    """Read/write access to places, including the spatial queries."""

    async def get_by_id(self, place_id: int) -> Place | None: ...

    async def get_by_source_id(self, source: str, source_id: str) -> Place | None: ...

    async def get_by_slug(self, slug: str) -> Place | None: ...

    async def list_pending_reviews(self, limit: int = 50) -> list[PendingDuplicate]:
        """Places the importer flagged for review, scored candidate first."""
        ...

    async def set_review_state(
        self,
        place_id: int,
        canonical_id: int | None,
        duplicate_of_id: int | None,
        operating_status: str,
    ) -> Place:
        """Move a place out of the review queue without ever deleting it."""
        ...

    async def add_review_decision(self, decision: ReviewDecision) -> None: ...

    async def count_by_source(self) -> list[tuple[str, int]]:
        """Places per ``source``."""
        ...

    async def unresolved_categories(self, limit: int | None = None) -> list[tuple[str, int]]:
        """``(raw source value, count)`` for imported places whose category did not resolve."""
        ...

    async def add(self, place: Place) -> Place: ...

    async def update(self, place: Place) -> Place: ...

    async def list_near(
        self,
        lat: float,
        lng: float,
        radius: float,
        *,
        q: str | None = None,
        criterion_ids: Sequence[int] = (),
        family: HandicapFamily | None = None,
        limit: int = 50,
    ) -> list[PlaceHit]:
        """Distance-sorted places around a point, optionally filtered."""
        ...

    async def get_candidates(
        self,
        lat: float,
        lng: float,
        name: str,
        *,
        radius: float = DEFAULT_CANDIDATE_RADIUS,
        limit: int = 50,
    ) -> list[PlaceHit]:
        """Places within ``radius`` metres of the point, for name scoring by the caller."""
        ...

    async def list_accessibility(self, place_id: int) -> list[PlaceAccessibility]: ...

    async def upsert_accessibility(
        self, place_id: int, values: dict[str, dict[str, object]]
    ) -> None:
        """Write values keyed by criterion slug; unknown slugs are ignored."""
        ...

    async def upsert_photos(self, place_id: int, photos: Sequence[PlacePhoto]) -> None: ...

    async def list_photos(self, place_id: int) -> list[PlacePhoto]: ...

    async def list_reviews(
        self, place_id: int, *, page: int, size: int
    ) -> tuple[list[Review], int]:
        """Published reviews, newest first, plus the total count."""
        ...

    async def review_stats(self, place_id: int) -> tuple[float | None, int]:
        """Average rating (one decimal) and published review count."""
        ...

    async def add_contribution(
        self, place_id: int, user_id: int, criterion_id: int, value: dict[str, object]
    ) -> None: ...

    async def add_review(
        self,
        place_id: int,
        user_id: int,
        rating: int,
        body: str,
        author_name: str | None,
    ) -> Review: ...

    async def set_review_status(self, review_id: int, status: str) -> Review | None: ...


class PlaceAliasRepository(Protocol):
    """Names a place is also known by (kept when a duplicate is merged)."""

    async def add(self, place_id: int, name: str) -> None: ...

    async def list_for_place(self, place_id: int) -> list[str]: ...


class MergeLogRepository(Protocol):
    """Audit trail of every soft merge (nothing is ever deleted)."""

    async def add(
        self, kept_id: int, merged_id: int, score: float, actor: str = "importer"
    ) -> None: ...


class CoverageRepository(Protocol):
    """Aggregate counts for the coverage export (read-only, safe on production)."""

    async def by_category_country(self) -> list[tuple[str, str, int, int]]:
        """``(category slug or '(unresolved)', country, places, places with values)``."""
        ...


class CategoryMappingRepository(Protocol):
    """Resolve a source vocabulary term to one of our categories."""

    async def resolve_slug(self, slug: str) -> int | None: ...
