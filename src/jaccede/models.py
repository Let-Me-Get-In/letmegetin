"""Modèles du référentiel d'accessibilité."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base déclarative SQLAlchemy."""


class TimestampMixin:
    """Colonnes created/updated communes."""

    created: Mapped[datetime] = mapped_column(server_default=func.now())
    updated: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class Category(Base, TimestampMixin):
    """Catégorie de lieu (restaurant, hôtel, pharmacie…)."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    label: Mapped[dict] = mapped_column(JSONB, default=dict)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)


class Criterion(Base, TimestampMixin):
    """Critère d'accessibilité hiérarchique et typé (groupe → critère → option)."""

    __tablename__ = "criteria"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("criteria.id"), index=True)
    type: Mapped[str] = mapped_column(String(16), default="boolean")
    position: Mapped[int] = mapped_column(default=0)
    need_children: Mapped[bool] = mapped_column(default=False)
    label: Mapped[dict] = mapped_column(JSONB, default=dict)
    description: Mapped[dict] = mapped_column(JSONB, default=dict)


class CategoryCriterion(Base):
    """Association catégorie ↔ critère."""

    __tablename__ = "category_criteria"

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )
    criterion_id: Mapped[int] = mapped_column(
        ForeignKey("criteria.id", ondelete="CASCADE"), primary_key=True
    )


class AccessibilityFilter(Base, TimestampMixin):
    """Filtre d'accessibilité exposé à la recherche."""

    __tablename__ = "accessibility_filters"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    label: Mapped[dict] = mapped_column(JSONB, default=dict)
    criterion_id: Mapped[int | None] = mapped_column(ForeignKey("criteria.id"))
    position: Mapped[int] = mapped_column(default=0)
    active: Mapped[bool] = mapped_column(default=True)


class OtherInformation(Base, TimestampMixin):
    """Label officiel / information complémentaire (ex. Tourisme & Handicap)."""

    __tablename__ = "other_information"
    __table_args__ = (UniqueConstraint("name", name="other_information_name_uc"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    label: Mapped[dict] = mapped_column(JSONB, default=dict)
    link: Mapped[str | None] = mapped_column(String(500))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("other_information.id"))
