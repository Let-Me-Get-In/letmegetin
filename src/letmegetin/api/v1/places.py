"""Places API v1 endpoints (presentation layer)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from letmegetin.api.deps import CategoryGridRepo, CriterionRepo, PlaceRepo
from letmegetin.api.schemas.places import (
    CandidateOut,
    PlaceDetailOut,
    PlaceSummaryOut,
    ReviewPageOut,
)
from letmegetin.application.places.candidates import find_candidates
from letmegetin.application.places.get_place import get_place
from letmegetin.application.places.list_reviews import list_reviews
from letmegetin.application.places.search import (
    DEFAULT_LIMIT,
    DEFAULT_RADIUS_METRES,
    search_places,
)
from letmegetin.core.exceptions import PlaceNotFound
from letmegetin.domain.referential.entities import HandicapFamily

router = APIRouter(prefix="/api/v1", tags=["places"])


def _criterion_ids(raw: str | None) -> list[int]:
    if not raw:
        return []
    try:
        return [int(part) for part in raw.split(",") if part.strip()]
    except ValueError:
        raise HTTPException(
            status_code=422, detail="filters must be comma-separated criterion ids"
        ) from None


@router.get("/places", response_model=list[PlaceSummaryOut])
async def search(
    places: PlaceRepo,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    radius: Annotated[float, Query(gt=0, le=50_000)] = DEFAULT_RADIUS_METRES,
    q: Annotated[str | None, Query(max_length=120)] = None,
    filters: Annotated[str | None, Query(description="Comma-separated criterion ids")] = None,
    family: HandicapFamily | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = DEFAULT_LIMIT,
) -> list[PlaceSummaryOut]:
    """Search places by proximity, text and accessibility filters, nearest first."""
    hits = await search_places(
        places,
        lat,
        lng,
        radius,
        q=q,
        criterion_ids=_criterion_ids(filters),
        family=family,
        limit=limit,
    )
    return [PlaceSummaryOut.from_place(hit.place, hit.distance) for hit in hits]


@router.get("/places/candidates", response_model=list[CandidateOut])
async def candidates(
    places: PlaceRepo,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    name: Annotated[str, Query(min_length=1, max_length=255)],
) -> list[CandidateOut]:
    """Nearby places with a similar name, so the UI can prevent a duplicate."""
    hits = await find_candidates(places, lat, lng, name)
    return [CandidateOut.from_hit(hit) for hit in hits]


@router.get("/places/{slug}", response_model=PlaceDetailOut)
async def place_detail(
    slug: str, places: PlaceRepo, criteria: CriterionRepo, grids: CategoryGridRepo
) -> PlaceDetailOut:
    """Return one place with its accessibility tree, reviews summary and photos, or 404."""
    try:
        detail = await get_place(places, criteria, grids, slug)
    except PlaceNotFound:
        raise HTTPException(status_code=404, detail="Place not found") from None
    return PlaceDetailOut.from_detail(detail)


@router.get("/places/{slug}/reviews", response_model=ReviewPageOut)
async def place_reviews(
    slug: str,
    places: PlaceRepo,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ReviewPageOut:
    """Return a place's published reviews, newest first, or 404."""
    try:
        reviews = await list_reviews(places, slug, page=page, size=size)
    except PlaceNotFound:
        raise HTTPException(status_code=404, detail="Place not found") from None
    return ReviewPageOut.from_page(reviews)
