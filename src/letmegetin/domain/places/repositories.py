"""Repository ports for the places context (implemented in infrastructure)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from letmegetin.domain.places.entities import (
    DedupRow,
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

    async def list_for_dedup(self, limit: int | None = None) -> list[DedupRow]:
        """Places with a location and no canonical parent, for the duplicate pass."""

    async def set_duplicate_candidate(self, place_id: int, candidate_id: int, score: float) -> None:
        """Record a 0.75-0.90 candidate so the operator can review it."""

    async def clear_duplicate_candidates(self) -> int:
        """Drop every pending candidate, so a recompute shows only what it still finds."""

    async def list_pending_reviews(
        self, limit: int = 50, min_confidence: float | None = None
    ) -> list[PendingDuplicate]:
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

    async def reassign_category(self, source_category: str, category_id: int) -> int:
        """Point every still-uncategorised place of one source value at ``category_id``."""
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
        category_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PlaceHit]:
        """Distance-sorted places around a point, optionally filtered.

        ``category_id`` narrows to one resolved category; the caller resolves the slug.
        The order is total (distance, then place id), so callers may page the result with
        ``limit``/``offset`` without a row repeating or disappearing between pages.
        """
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

    async def list_accessibility_for_places(
        self, place_ids: Sequence[int]
    ) -> dict[int, list[PlaceAccessibility]]:
        """Recorded values of several places in ONE query, keyed by place id.

        A place with no recorded value has no key: callers must treat the missing key as
        "undocumented", never as an error (D-06).
        """
        ...

    async def upsert_accessibility(
        self,
        place_id: int,
        values: dict[str, dict[str, object]],
        *,
        source: str,
        actor: str,
        observed_at: datetime | None = None,
    ) -> None:
        """Write values keyed by criterion slug; unknown slugs are ignored.

        The single shared write path (D-09…D-12): a contribution (``source='user'``) takes
        ownership of the row; an import may only replace a row of its own source and only with
        an ``observed_at`` at least as fresh (NULL counts as the oldest claim). A criterion the
        place does not hold yet is always inserted. Every attempt is appended to the write
        journal, so a rejected value stays visible to an operator.

        The licence is resolved from the reviewed ``source_licence`` table at write time, never
        passed in (LIC-05); an unmapped source raises ``DomainError`` (D-15).
        """
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
