"""Repository ports for the places context (implemented in infrastructure)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from letmegetin.domain.places.entities import (
    HandicapFamily,
    Place,
    PlaceAccessibility,
    PlaceHit,
)

DEFAULT_CANDIDATE_RADIUS = 100.0


class PlaceRepository(Protocol):
    """Read/write access to places, including the spatial queries."""

    async def get_by_source_id(self, source: str, source_id: str) -> Place | None: ...

    async def get_by_slug(self, slug: str) -> Place | None: ...

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
    ) -> list[Place]:
        """Places within ``radius`` metres of the point, for name scoring by the caller."""
        ...

    async def list_accessibility(self, place_id: int) -> list[PlaceAccessibility]: ...


class PlaceAliasRepository(Protocol):
    """Names a place is also known by (kept when a duplicate is merged)."""

    async def add(self, place_id: int, name: str) -> None: ...

    async def list_for_place(self, place_id: int) -> list[str]: ...


class MergeLogRepository(Protocol):
    """Audit trail of every soft merge (nothing is ever deleted)."""

    async def add(
        self, kept_id: int, merged_id: int, score: float, actor: str = "importer"
    ) -> None: ...


class CategoryMappingRepository(Protocol):
    """Resolve a source vocabulary term to one of our categories."""

    async def resolve_slug(self, slug: str) -> int | None: ...
