"""Map ORM models to domain entities (anti-corruption layer)."""

from __future__ import annotations

from letmegetin.domain.places.entities import Place, PlaceAccessibility
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
    PlaceAccessibilityModel,
    PlaceModel,
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
        handicap_families=list(model.handicap_families or []),
        en17210_ref=model.en17210_ref,
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
        id=model.id,
        slug=model.slug,
        label=model.label,
        position=model.position,
        handicap_families=list(model.handicap_families or []),
    )


def place_from_model(model: PlaceModel) -> Place:
    return Place(
        id=model.id,
        name=model.name,
        slug=model.slug,
        source=model.source,
        source_id=model.source_id,
        category_id=model.category_id,
        address_full=model.address_full,
        city=model.city,
        postal_code=model.postal_code,
        country_code=model.country_code,
        lat=model.lat,
        lng=model.lng,
        operating_status=model.operating_status,
        confidence=model.confidence,
        website=model.website,
        phone=model.phone,
        canonical_id=model.canonical_id,
    )


def place_accessibility_from_models(
    value: PlaceAccessibilityModel, criterion: CriterionModel
) -> PlaceAccessibility:
    return PlaceAccessibility(
        criterion_slug=criterion.slug,
        label=criterion.label,
        handicap_families=list(criterion.handicap_families or []),
        value=value.value,
    )


def other_information_from_model(model: OtherInformationModel) -> OtherInformation:
    return OtherInformation(
        id=model.id, slug=model.slug, name=model.name, label=model.label, link=model.link
    )
