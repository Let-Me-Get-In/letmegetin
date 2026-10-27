"""Pydantic response schemas exposed by the places API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from letmegetin.application.places.get_place import PlaceDetail
from letmegetin.application.places.list_reviews import ReviewPage
from letmegetin.domain.places.entities import Place, PlaceHit, Review


class PlaceSummaryOut(BaseModel):
    """A place in a search result list."""

    slug: str
    name: str
    category: str | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    distance: float | None = None
    operating_status: str

    @classmethod
    def from_place(cls, place: Place, distance: float | None = None) -> PlaceSummaryOut:
        return cls(
            slug=place.slug,
            name=place.name,
            category=place.category_slug,
            address=place.address_full,
            lat=place.lat,
            lng=place.lng,
            distance=round(distance, 1) if distance is not None else None,
            operating_status=place.operating_status,
        )


class AccessibilityValueOut(BaseModel):
    """One accessibility value recorded for a place."""

    criterion: str
    label: dict[str, str]
    handicap_families: list[str]
    value: dict[str, Any]


class PhotoOut(BaseModel):
    """A source photo of the place."""

    url: str
    credit: str | None = None
    license: str | None = None


class ReviewOut(BaseModel):
    """One published review."""

    id: int
    rating: int
    body: str
    author_name: str | None = None
    created: datetime
    status: str = "published"

    @classmethod
    def from_review(cls, review: Review) -> ReviewOut:
        return cls(
            id=review.id,
            rating=review.rating,
            body=review.body,
            author_name=review.author_name,
            created=review.created,
            status=review.status,
        )


class ReviewIn(BaseModel):
    """Review creation payload."""

    rating: int = Field(ge=1, le=5)
    body: str = Field(default="", max_length=5000)


class ReviewStatusIn(BaseModel):
    """Admin moderation payload."""

    status: Literal["published", "hidden"]


class ContributionIn(BaseModel):
    """One accessibility value written by an authenticated user."""

    value: Any


class ContributionOut(BaseModel):
    """The written value plus the recomputed completion rate."""

    criterion: str
    value: Any
    filled_rate: float


class ReviewPageOut(BaseModel):
    """A page of reviews plus the total count."""

    items: list[ReviewOut]
    total: int
    page: int
    size: int

    @classmethod
    def from_page(cls, page: ReviewPage) -> ReviewPageOut:
        return cls(
            items=[
                ReviewOut(
                    id=review.id,
                    rating=review.rating,
                    body=review.body,
                    author_name=review.author_name,
                    created=review.created,
                )
                for review in page.items
            ],
            total=page.total,
            page=page.page,
            size=page.size,
        )


class PlaceDetailOut(PlaceSummaryOut):
    """A place record with its accessibility tree and reviews (PLACE-03/04, REV-01)."""

    accessibility: list[AccessibilityValueOut] = []
    accessibility_by_family: dict[str, float] = {}
    tree: list[dict[str, Any]] = []
    filled_rate: float = 0.0
    photos: list[PhotoOut] = []
    rating: float | None = None
    review_count: int = 0

    @classmethod
    def from_detail(cls, detail: PlaceDetail) -> PlaceDetailOut:
        summary = PlaceSummaryOut.from_place(detail.place)
        return cls(
            **summary.model_dump(),
            accessibility=[
                AccessibilityValueOut(
                    criterion=value.criterion_slug,
                    label=value.label,
                    handicap_families=value.handicap_families,
                    value=value.value,
                )
                for value in detail.accessibility
            ],
            accessibility_by_family=detail.accessibility_by_family,
            tree=detail.tree,
            filled_rate=detail.filled_rate,
            photos=[
                PhotoOut(url=photo.url, credit=photo.credit, license=photo.license)
                for photo in detail.photos
            ],
            rating=detail.rating,
            review_count=detail.review_count,
        )


class CandidateOut(BaseModel):
    """A nearby place that may already be the one being created."""

    slug: str
    name: str
    distance: float
    score: float

    @classmethod
    def from_hit(cls, hit: PlaceHit) -> CandidateOut:
        return cls(
            slug=hit.place.slug,
            name=hit.place.name,
            distance=round(hit.distance, 1),
            score=hit.score,
        )
