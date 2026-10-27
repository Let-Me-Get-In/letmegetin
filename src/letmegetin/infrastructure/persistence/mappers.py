"""Map ORM models to domain entities (anti-corruption layer)."""

from __future__ import annotations

from letmegetin.domain.referential.entities import (
    AccessibilityFilter,
    Category,
    Criterion,
    OtherInformation,
)
from letmegetin.infrastructure.persistence.models import (
    AccessibilityFilterModel,
    CategoryModel,
    CriterionModel,
    OtherInformationModel,
)


def category_from_model(model: CategoryModel) -> Category:
    return Category(id=model.id, slug=model.slug, name=model.name, label=model.label)


def criterion_from_model(model: CriterionModel) -> Criterion:
    return Criterion(
        id=model.id,
        slug=model.slug,
        parent_id=model.parent_id,
        type=model.type,
        position=model.position,
        label=model.label,
        description=model.description,
    )


def filter_from_model(model: AccessibilityFilterModel) -> AccessibilityFilter:
    return AccessibilityFilter(
        id=model.id, slug=model.slug, label=model.label, position=model.position
    )


def other_information_from_model(model: OtherInformationModel) -> OtherInformation:
    return OtherInformation(
        id=model.id, slug=model.slug, name=model.name, label=model.label, link=model.link
    )
