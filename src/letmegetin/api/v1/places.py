"""Places API v1 endpoints (presentation layer)."""

from __future__ import annotations

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse

from letmegetin.api.deps import (
    AdminUser,
    CategoryGridRepo,
    CriterionRepo,
    DbSession,
    PlaceRepo,
    VerifiedUser,
    public_rate_limit,
)
from letmegetin.api.idempotency import remember, replay
from letmegetin.api.schemas.places import (
    CandidateOut,
    ContributionIn,
    ContributionOut,
    PlaceDetailOut,
    PlaceSummaryOut,
    ReviewIn,
    ReviewOut,
    ReviewPageOut,
    ReviewStatusIn,
)
from letmegetin.application.places.candidates import find_candidates
from letmegetin.application.places.contribute import contribute
from letmegetin.application.places.get_place import get_place
from letmegetin.application.places.list_reviews import list_reviews
from letmegetin.application.places.reviews import create_review, set_review_status
from letmegetin.application.places.search import (
    DEFAULT_LIMIT,
    DEFAULT_RADIUS_METRES,
    search_places,
)
from letmegetin.core.exceptions import CriterionNotFound, PlaceNotFound, ReviewNotFound
from letmegetin.domain.referential.entities import HandicapFamily

router = APIRouter(prefix="/api/v1", tags=["places"], dependencies=[Depends(public_rate_limit)])


def _request_hash(method: str, path: str, body: str) -> str:
    return hashlib.sha256(f"{method}:{path}:{body}".encode()).hexdigest()


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


@router.put("/places/{slug}/accessibility/{criterion_slug}", response_model=ContributionOut)
async def write_accessibility(
    slug: str,
    criterion_slug: str,
    payload: ContributionIn,
    places: PlaceRepo,
    criteria: CriterionRepo,
    grids: CategoryGridRepo,
    user: VerifiedUser,
    session: DbSession,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=128)] = None,
) -> ContributionOut | JSONResponse:
    """Authenticated write of one accessibility value (CONTRIB-01/02)."""
    request_hash = _request_hash("PUT", f"{slug}/{criterion_slug}", payload.model_dump_json())
    replayed = await replay(session, user.id, idempotency_key, request_hash)
    if replayed is not None:
        return replayed
    try:
        await contribute(places, criteria, slug, criterion_slug, user, payload.value)
        detail = await get_place(places, criteria, grids, slug)
    except PlaceNotFound:
        raise HTTPException(status_code=404, detail="Place not found") from None
    except CriterionNotFound:
        raise HTTPException(status_code=404, detail="Criterion not found") from None
    response = ContributionOut(
        criterion=criterion_slug, value=payload.value, filled_rate=detail.filled_rate
    )
    await remember(
        session,
        user.id,
        idempotency_key,
        request_hash,
        200,
        response.model_dump(mode="json"),
    )
    await session.commit()
    return response


@router.post("/places/{slug}/reviews", response_model=ReviewOut, status_code=201)
async def write_review(
    slug: str,
    payload: ReviewIn,
    places: PlaceRepo,
    user: VerifiedUser,
    session: DbSession,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=128)] = None,
) -> ReviewOut | JSONResponse:
    """Authenticated review creation (REV-02)."""
    request_hash = _request_hash("POST", slug, payload.model_dump_json())
    replayed = await replay(session, user.id, idempotency_key, request_hash)
    if replayed is not None:
        return replayed
    try:
        review = await create_review(places, slug, user, payload.rating, payload.body)
    except PlaceNotFound:
        raise HTTPException(status_code=404, detail="Place not found") from None
    response = ReviewOut.from_review(review)
    await remember(
        session,
        user.id,
        idempotency_key,
        request_hash,
        201,
        response.model_dump(mode="json"),
    )
    await session.commit()
    return response


@router.patch("/reviews/{review_id}", response_model=ReviewOut)
async def moderate_review(
    review_id: int,
    payload: ReviewStatusIn,
    places: PlaceRepo,
    admin: AdminUser,
    session: DbSession,
) -> ReviewOut:
    """Admin-only hide/publish of a review (AUTH-03)."""
    try:
        review = await set_review_status(places, review_id, payload.status)
    except ReviewNotFound:
        raise HTTPException(status_code=404, detail="Review not found") from None
    await session.commit()
    return ReviewOut.from_review(review)
