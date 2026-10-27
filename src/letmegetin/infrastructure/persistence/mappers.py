"""Map ORM models to domain entities (anti-corruption layer)."""

from __future__ import annotations

from letmegetin.domain.referential.entities import (
    AccessibilityFilter,
    Category,
    Criterion,
    OtherInformation,
    VocabularyEntry,
)
from letmegetin.infrastructure.persistence.models import (
    AccessibilityFilterModel,
    CategoryModel,
    CriterionModel,
    CriterionVocabularyModel,
    OtherInformationModel,
)


def category_from_model(model: CategoryModel) -> Category:
    return Category(
        id=model.id,
        slug=model.slug,
        name=model.name,
        label=model.label,
        parent_id=model.parent_id,
    )


def criterion_from_model(model: CriterionModel) -> Criterion:
    return Criterion(
        id=model.id,
        slug=model.slug,
        parent_id=model.parent_id,
        type=model.type,
        position=model.position,
        label=model.label,
        description=model.description,
        is_default=model.is_default,
    )


def vocabulary_from_model(model: CriterionVocabularyModel) -> VocabularyEntry:
    return VocabularyEntry(
        id=model.id,
        slug=model.slug,
        label=model.label,
        description=model.description,
        promoted_criterion_id=model.promoted_criterion_id,
    )


def filter_from_model(model: AccessibilityFilterModel) -> AccessibilityFilter:
    return AccessibilityFilter(
        id=model.id, slug=model.slug, label=model.label, position=model.position
    )


def other_information_from_model(model: OtherInformationModel) -> OtherInformation:
    return OtherInformation(
        id=model.id, slug=model.slug, name=model.name, label=model.label, link=model.link
    )
