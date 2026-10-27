"""Admin use cases: curate the referential (vocabulary, categories, criteria, mapping).

Ordering-sensitive design: the default mapping lives on ``criteria.is_default`` and the
per-category overrides on ``category_criteria.excluded``, so a re-run of the seed never
overwrites an operator decision.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from letmegetin.application.referential.get_category_tree import build_tree, tree_to_json
from letmegetin.core.exceptions import (
    CategoryAlreadyExists,
    CategoryNotFound,
    CriterionNotFound,
    DomainError,
    VocabularyNotFound,
)
from letmegetin.core.utils import slugify
from letmegetin.domain.referential.entities import (
    HANDICAP_FAMILIES,
    Category,
    CategoryMapping,
    Criterion,
    Label,
    VocabularyEntry,
)
from letmegetin.domain.referential.labels import merge_label, normalize_label
from letmegetin.domain.referential.repositories import (
    CategoryGridRepository,
    CategoryRepository,
    CriterionRepository,
    MappingAdminRepository,
    MappingRepository,
    VocabularyRepository,
)

CRITERION_TYPES: tuple[str, ...] = ("array", "option", "boolean", "integer", "string")


@dataclass
class ImportReport:
    """Outcome of a vocabulary import: rows created and rows already present."""

    created: int
    skipped: int


def _validated_type(kind: str) -> str:
    if kind not in CRITERION_TYPES:
        allowed = ", ".join(CRITERION_TYPES)
        raise DomainError(f"unsupported criterion type '{kind}' (allowed: {allowed})")
    return kind


async def _require_category(repository: CategoryRepository, slug: str) -> Category:
    category = await repository.get_by_slug(slug)
    if category is None:
        raise CategoryNotFound(slug)
    return category


async def _require_criterion(repository: CriterionRepository, slug: str) -> Criterion:
    criterion = await repository.get_by_slug(slug)
    if criterion is None:
        raise CriterionNotFound(slug)
    return criterion


async def _resolve_parent(repository: CriterionRepository, parent_slug: str | None) -> int | None:
    if parent_slug is None:
        return None
    return (await _require_criterion(repository, parent_slug)).id


def load_vocabulary_file(path: Path) -> list[VocabularyEntry]:
    """Read a JSON list of ``{slug, label, description}`` objects into vocabulary entries."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries: list[VocabularyEntry] = []
    for item in raw:
        slug = item.get("slug")
        if not slug:
            raise DomainError("vocabulary entry is missing a slug")
        label = item.get("label") or {}
        if not label:
            raise DomainError(f"vocabulary entry '{slug}' has no label")
        entries.append(
            VocabularyEntry(
                id=0,
                slug=slug,
                label=label,
                description=item.get("description") or {},
            )
        )
    return entries


async def import_vocabulary(
    repository: VocabularyRepository, entries: list[VocabularyEntry]
) -> ImportReport:
    """Upsert vocabulary entries by slug; existing slugs are left untouched."""
    created = 0
    skipped = 0
    for entry in entries:
        if await repository.get_by_slug(entry.slug) is not None:
            skipped += 1
            continue
        await repository.add(entry)
        created += 1
    return ImportReport(created=created, skipped=skipped)


async def add_category(
    repository: CategoryRepository, slug: str, name: str, label: Label | None = None
) -> Category:
    """Create a category; the slug must be free."""
    if await repository.get_by_slug(slug) is not None:
        raise CategoryAlreadyExists(slug)
    return await repository.add(
        Category(id=0, slug=slug, name=name, label=normalize_label(label or {}))
    )


async def edit_category(
    repository: CategoryRepository,
    slug: str,
    name: str | None = None,
    label: Label | None = None,
    parent_slug: str | None = None,
) -> Category:
    """Edit a category in place: labels are merged, never replaced."""
    category = await _require_category(repository, slug)
    parent_id = category.parent_id
    if parent_slug is not None:
        parent_id = (await _require_category(repository, parent_slug)).id
    return await repository.update(
        replace(
            category,
            name=name if name is not None else category.name,
            label=merge_label(category.label, label or {}),
            parent_id=parent_id,
        )
    )


async def add_criterion(
    repository: CriterionRepository,
    slug: str,
    kind: str,
    label: Label | None = None,
    parent_slug: str | None = None,
    description: Label | None = None,
    is_default: bool = False,
) -> Criterion:
    """Create a criterion, option or group; the parent is resolved by slug."""
    criterion_type = _validated_type(kind)
    if await repository.get_by_slug(slug) is not None:
        raise DomainError(f"Criterion '{slug}' already exists")
    return await repository.add(
        Criterion(
            id=0,
            slug=slug,
            parent_id=await _resolve_parent(repository, parent_slug),
            type=criterion_type,
            position=0,
            label=normalize_label(label or {}),
            description=normalize_label(description or {}),
            is_default=is_default,
        )
    )


async def edit_criterion(
    repository: CriterionRepository,
    slug: str,
    kind: str | None = None,
    label: Label | None = None,
    description: Label | None = None,
    is_default: bool | None = None,
    parent_slug: str | None = None,
    families: list[str] | None = None,
    en17210_ref: str | None = None,
) -> Criterion:
    """Edit a criterion in place: labels and descriptions are merged, never replaced."""
    criterion = await _require_criterion(repository, slug)
    parent_id = criterion.parent_id
    if parent_slug is not None:
        parent_id = await _resolve_parent(repository, parent_slug)
    return await repository.update(
        replace(
            criterion,
            parent_id=parent_id,
            type=_validated_type(kind) if kind is not None else criterion.type,
            label=merge_label(criterion.label, label or {}),
            description=merge_label(criterion.description, description or {}),
            is_default=criterion.is_default if is_default is None else is_default,
            handicap_families=(
                _validated_families(families)
                if families is not None
                else criterion.handicap_families
            ),
            en17210_ref=(criterion.en17210_ref if en17210_ref is None else en17210_ref or None),
        )
    )


def _validated_families(families: list[str]) -> list[str]:
    unknown = [family for family in families if family not in HANDICAP_FAMILIES]
    if unknown:
        allowed = ", ".join(HANDICAP_FAMILIES)
        raise DomainError(f"unsupported handicap family '{unknown[0]}' (allowed: {allowed})")
    return [family for family in HANDICAP_FAMILIES if family in families]


async def set_criterion_families(
    repository: CriterionRepository, slug: str, families: list[str]
) -> Criterion:
    """Replace the handicap families a criterion belongs to."""
    criterion = await _require_criterion(repository, slug)
    return await repository.update(
        replace(criterion, handicap_families=_validated_families(families))
    )


async def map_category(
    mapping: MappingAdminRepository,
    categories: CategoryRepository,
    slug: str,
    overture_category: str | None = None,
    osm_tag: str | None = None,
    acceslibre_family: str | None = None,
    notes: str | None = None,
) -> Category:
    """Upsert the source-vocabulary mapping of a category."""
    category = await _require_category(categories, slug)
    await mapping.upsert(
        CategoryMapping(
            category_id=category.id,
            overture_category=overture_category,
            osm_tag=osm_tag,
            acceslibre_family=acceslibre_family,
            notes=notes,
        )
    )
    return category


async def rebuild_category_grids(
    categories: CategoryRepository,
    criteria: CriterionRepository,
    grids: CategoryGridRepository,
) -> int:
    """Bump the referential version and recompute every precomputed category grid."""
    version = await grids.bump_version()
    for category in await categories.list_all():
        tree = build_tree(await criteria.list_for_category(category.id))
        await grids.set_grid(category.id, version, tree_to_json(tree))
    return version


async def link_criterion(
    categories: CategoryRepository,
    criteria: CriterionRepository,
    mapping: MappingRepository,
    category_slug: str,
    criterion_slug: str,
) -> str:
    """Make a criterion apply to a category (clears any explicit exclusion for a default)."""
    category = await _require_category(categories, category_slug)
    criterion = await _require_criterion(criteria, criterion_slug)
    state: Literal["include", "clear"] = "clear" if criterion.is_default else "include"
    await mapping.set_state(category.id, criterion.id, state)
    return f"{criterion_slug} linked to {category_slug}"


async def unlink_criterion(
    categories: CategoryRepository,
    criteria: CriterionRepository,
    mapping: MappingRepository,
    category_slug: str,
    criterion_slug: str,
) -> str:
    """Stop a criterion applying to a category (an exclusion row for a default)."""
    category = await _require_category(categories, category_slug)
    criterion = await _require_criterion(criteria, criterion_slug)
    state: Literal["exclude", "clear"] = "exclude" if criterion.is_default else "clear"
    await mapping.set_state(category.id, criterion.id, state)
    return f"{criterion_slug} unlinked from {category_slug}"


async def promote_vocabulary(
    vocabulary: VocabularyRepository,
    criteria: CriterionRepository,
    mapping: MappingRepository,
    categories: CategoryRepository,
    slug: str,
    kind: str,
    parent_slug: str | None = None,
    category_slugs: list[str] | None = None,
) -> Criterion:
    """Turn a vocabulary entry into a criterion and link it to the requested categories."""
    entry = await vocabulary.get_by_slug(slug)
    if entry is None:
        raise VocabularyNotFound(slug)
    if entry.promoted_criterion_id is not None:
        raise DomainError(f"Vocabulary entry '{slug}' is already promoted")
    label = entry.label or {"fr": slug}
    criterion = await add_criterion(
        criteria,
        slugify(label.get("fr") or slug),
        kind,
        label=label,
        parent_slug=parent_slug,
        description=entry.description,
    )
    await vocabulary.update(replace(entry, promoted_criterion_id=criterion.id))
    for category_slug in category_slugs or []:
        category = await _require_category(categories, category_slug)
        await mapping.set_state(category.id, criterion.id, "include")
    return criterion


async def set_category_labels(repository: CategoryRepository, slug: str, label: Label) -> Category:
    """Merge a label map onto a category."""
    category = await _require_category(repository, slug)
    return await repository.update(replace(category, label=merge_label(category.label, label)))


async def set_criterion_labels(
    repository: CriterionRepository, slug: str, label: Label
) -> Criterion:
    """Merge a label map onto a criterion."""
    criterion = await _require_criterion(repository, slug)
    return await repository.update(replace(criterion, label=merge_label(criterion.label, label)))


async def set_vocabulary_labels(
    repository: VocabularyRepository, slug: str, label: Label
) -> VocabularyEntry:
    """Merge a label map onto a vocabulary entry."""
    entry = await repository.get_by_slug(slug)
    if entry is None:
        raise VocabularyNotFound(slug)
    return await repository.update(replace(entry, label=merge_label(entry.label, label)))
