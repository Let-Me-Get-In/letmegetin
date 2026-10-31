"""SQLAlchemy ORM models for the referential (infrastructure layer)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import geoalchemy2
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    Double,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# PostGIS derives the point from the plain lat/lng columns, so the two never drift.
_LOCATION_SQL = (
    "CASE WHEN lat IS NOT NULL AND lng IS NOT NULL "
    "THEN ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography END"
)


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


class TimestampMixin:
    """Common created/updated columns."""

    created: Mapped[datetime] = mapped_column(server_default=func.now())
    updated: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class UserModel(Base, TimestampMixin):
    """An account allowed to contribute and review."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), server_default="user")
    display_name: Mapped[str | None] = mapped_column(String(120))
    email_verified: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class ApiKeyModel(Base):
    """A partner API key (only the SHA-256 fingerprint is stored)."""

    __tablename__ = "api_key"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(120))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    rpm: Mapped[int] = mapped_column(Integer, server_default="60")
    active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created: Mapped[datetime] = mapped_column(server_default=func.now())


class RefreshTokenModel(Base):
    """A refresh token the server can revoke (only its SHA-256 fingerprint is stored)."""

    __tablename__ = "refresh_token"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column()
    revoked: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created: Mapped[datetime] = mapped_column(server_default=func.now())


class ContributionModel(Base):
    """Append-only audit log of an authenticated accessibility write (CONTRIB-02)."""

    __tablename__ = "contribution"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("place.id", ondelete="CASCADE"), index=True)
    criterion_id: Mapped[int] = mapped_column(ForeignKey("criteria.id", ondelete="CASCADE"))
    value: Mapped[dict] = mapped_column(JSONB, default=dict)
    created: Mapped[datetime] = mapped_column(server_default=func.now())


class CategoryModel(Base, TimestampMixin):
    """Place categories (restaurant, hotel, pharmacy…)."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    label: Mapped[dict] = mapped_column(JSONB, default=dict)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)


class CriterionModel(Base, TimestampMixin):
    """Hierarchical, typed accessibility criteria (group → criterion → option)."""

    __tablename__ = "criteria"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("criteria.id"), index=True)
    type: Mapped[str] = mapped_column(String(16), default="boolean")
    position: Mapped[int] = mapped_column(default=0)
    need_children: Mapped[bool] = mapped_column(default=False)
    is_default: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    label: Mapped[dict] = mapped_column(JSONB, default=dict)
    description: Mapped[dict] = mapped_column(JSONB, default=dict)
    handicap_families: Mapped[list[str]] = mapped_column(
        ARRAY(String(16)), default=list, server_default=text("'{}'")
    )
    en17210_ref: Mapped[str | None] = mapped_column(String(64))


class CategoryCriterionModel(Base):
    """Association between a category and a criterion."""

    __tablename__ = "category_criteria"

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )
    criterion_id: Mapped[int] = mapped_column(
        ForeignKey("criteria.id", ondelete="CASCADE"), primary_key=True
    )
    excluded: Mapped[bool] = mapped_column(default=False, server_default=text("false"))


class CriterionVocabularyModel(Base, TimestampMixin):
    """Flat vocabulary of criteria labels, promoted into `criteria` on demand."""

    __tablename__ = "criterion_vocabulary"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    label: Mapped[dict] = mapped_column(JSONB, default=dict)
    description: Mapped[dict] = mapped_column(JSONB, default=dict)
    promoted_criterion_id: Mapped[int | None] = mapped_column(
        ForeignKey("criteria.id", ondelete="SET NULL")
    )


class AccessibilityFilterModel(Base, TimestampMixin):
    """Accessibility filter exposed to search."""

    __tablename__ = "accessibility_filters"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    label: Mapped[dict] = mapped_column(JSONB, default=dict)
    criterion_id: Mapped[int | None] = mapped_column(ForeignKey("criteria.id"))
    position: Mapped[int] = mapped_column(default=0)
    active: Mapped[bool] = mapped_column(default=True)
    handicap_families: Mapped[list[str]] = mapped_column(
        ARRAY(String(16)), default=list, server_default=text("'{}'")
    )


class OtherInformationModel(Base, TimestampMixin):
    """Official label / complementary information (e.g. Tourisme & Handicap)."""

    __tablename__ = "other_information"
    __table_args__ = (UniqueConstraint("name", name="other_information_name_uc"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    label: Mapped[dict] = mapped_column(JSONB, default=dict)
    link: Mapped[str | None] = mapped_column(String(500))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("other_information.id"))


class PlaceModel(Base, TimestampMixin):
    """A physical place (Acceslibre, Overture, OSM or user-created)."""

    __tablename__ = "place"
    __table_args__ = (
        Index(
            "place_source_source_id_uc",
            "source",
            "source_id",
            unique=True,
            postgresql_where=text("source_id IS NOT NULL"),
        ),
        Index("ix_place_location", "location", postgresql_using="gist"),
        Index(
            "ix_place_name_normalized",
            "name_normalized",
            postgresql_using="gin",
            postgresql_ops={"name_normalized": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str | None] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    name_normalized: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(300), unique=True, index=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    address_full: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str | None] = mapped_column(String(120))
    postal_code: Mapped[str | None] = mapped_column(String(16))
    country_code: Mapped[str] = mapped_column(String(2), server_default="FR")
    lat: Mapped[float | None] = mapped_column(Double)
    lng: Mapped[float | None] = mapped_column(Double)
    location: Mapped[Any] = mapped_column(
        geoalchemy2.Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        Computed(_LOCATION_SQL, persisted=True),
        nullable=True,
    )
    operating_status: Mapped[str] = mapped_column(String(32), server_default="open")
    confidence: Mapped[float | None] = mapped_column(Double)
    website: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(32))
    canonical_id: Mapped[int | None] = mapped_column(
        ForeignKey("place.id", ondelete="SET NULL"), index=True
    )


class PlaceAliasModel(Base):
    """A name a place is also known by (kept when a duplicate is merged)."""

    __tablename__ = "place_alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("place.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))


class PlaceMergeLogModel(Base):
    """Audit trail of every soft merge; nothing is deleted."""

    __tablename__ = "place_merge_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    kept_id: Mapped[int] = mapped_column(ForeignKey("place.id", ondelete="CASCADE"), index=True)
    merged_id: Mapped[int] = mapped_column(ForeignKey("place.id", ondelete="CASCADE"))
    score: Mapped[float] = mapped_column(Double)
    actor: Mapped[str] = mapped_column(String(32), server_default="importer")
    created: Mapped[datetime] = mapped_column(server_default=func.now())


class PlaceAccessibilityModel(Base):
    """One recorded accessibility value for a place (PLACE-04 skeleton)."""

    __tablename__ = "place_accessibility"

    place_id: Mapped[int] = mapped_column(
        ForeignKey("place.id", ondelete="CASCADE"), primary_key=True
    )
    criterion_id: Mapped[int] = mapped_column(
        ForeignKey("criteria.id", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[dict] = mapped_column(JSONB, default=dict)


class ReviewModel(Base, TimestampMixin):
    """A published review for a place (write path arrives with auth, Phase 5)."""

    __tablename__ = "review"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="review_rating_range"),
        Index("ix_review_place_created", "place_id", "created"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("place.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(SmallInteger)
    body: Mapped[str] = mapped_column(Text, default="")
    author_name: Mapped[str | None] = mapped_column(String(120))
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), server_default="published")


class PlacePhotoModel(Base):
    """A source photo of the place (never invented; license kept per row)."""

    __tablename__ = "place_photo"
    __table_args__ = (UniqueConstraint("place_id", "url", name="place_photo_url_uc"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("place.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(1000))
    credit: Mapped[str | None] = mapped_column(String(255))
    license: Mapped[str | None] = mapped_column(String(64))


class CategoryMappingModel(Base, TimestampMixin):
    """Map one of our categories to the Overture/OSM/Acceslibre vocabularies."""

    __tablename__ = "category_mapping"
    __table_args__ = (UniqueConstraint("category_id", name="category_mapping_category_uc"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
    overture_category: Mapped[str | None] = mapped_column(String(120))
    osm_tag: Mapped[str | None] = mapped_column(String(120))
    acceslibre_family: Mapped[str | None] = mapped_column(String(60))
    notes: Mapped[str | None] = mapped_column(String(500))


class CategoryGridModel(Base):
    """Precomputed per-category criteria tree (one row read per form)."""

    __tablename__ = "category_grid"

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )
    version: Mapped[int] = mapped_column(default=1)
    tree: Mapped[list] = mapped_column(JSONB, default=list)
    updated: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class ReferentialVersionModel(Base):
    """Single-row global referential version, bumped on every admin edit."""

    __tablename__ = "referential_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(default=1, server_default=text("1"))
