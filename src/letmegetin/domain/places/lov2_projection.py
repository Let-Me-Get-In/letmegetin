"""Project our keys into AccesLibre's vocabulary for the lov2 partner feed (D-05..D-08).

Pure module (no SQLAlchemy, no FastAPI). A place is keyed on the identifier the 15-03 probe
settled — ``resolve_identifier`` is the only place that rule becomes a key — its category is the
canonical ``activite``, and an answer's criterion is one of the 8 ``FIELD_MAP`` field names. A row
we cannot express is returned as an unmappable with its reason, never dropped and never guessed
(T-15-06); the caller writes those to the mapping document.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime

from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.acceslibre_push import resolve_identifier
from letmegetin.domain.places.export_plan import (
    AliasRow,
    AnswerRow,
    CategoryRow,
    CriterionRow,
    PlaceRow,
    _iso,
    _json_text,
)

# The partner vocabulary, column for column. Every header names their terms, never ours: no
# ``slug``/``category_slug``/``criterion_slug`` reaches the feed (prohibitions, PART-01).
LOV2_PLACES_HEADER = (
    "place_id",
    "identifier",
    "origin_id",
    "name",
    "activite",
    "source_category",
    "address_full",
    "city",
    "postal_code",
    "country_code",
    "lat",
    "lng",
    "operating_status",
    "website",
    "phone",
    "source",
    "source_license",
    "source_url",
    "date",
)
LOV2_CATEGORIES_HEADER = (
    "category_id",
    "activite",
    "parent_id",
    "parent_activite",
    "name",
    "label",
)
LOV2_CRITERIA_HEADER = (
    "criterion_id",
    "field",
    "parent_id",
    "parent_field",
    "type",
    "position",
    "handicap_families",
    "label",
    "en17210_ref",
)
LOV2_ANSWERS_HEADER = (
    "place_id",
    "field",
    "value",
    "source",
    "source_license",
    "source_url",
    "date",
)
MAPPING_HEADER = ("entity", "identifier", "reason", "detail")


@dataclass(frozen=True, slots=True)
class ProjectedPlace:
    """One place in their vocabulary; ``source``/``source_license``/``date`` drive ATTRIBUTION."""

    place_id: int
    identifier: str
    origin_id: str | None
    name: str
    activite: str | None
    source_category: str | None
    address_full: str | None
    city: str | None
    postal_code: str | None
    country_code: str
    lat: float | None
    lng: float | None
    operating_status: str
    website: str | None
    phone: str | None
    source: str
    source_license: str | None
    source_url: str | None
    date: datetime | None

    def to_csv(self) -> tuple[object, ...]:
        return (
            self.place_id,
            self.identifier,
            self.origin_id,
            self.name,
            self.activite,
            self.source_category,
            self.address_full,
            self.city,
            self.postal_code,
            self.country_code,
            self.lat,
            self.lng,
            self.operating_status,
            self.website,
            self.phone,
            self.source,
            self.source_license,
            self.source_url,
            _iso(self.date),
        )


@dataclass(frozen=True, slots=True)
class ProjectedCategory:
    """One category expressed as its canonical ``activite``."""

    category_id: int
    activite: str
    parent_id: int | None
    parent_activite: str | None
    name: str
    label: dict[str, object]

    def to_csv(self) -> tuple[object, ...]:
        return (
            self.category_id,
            self.activite,
            self.parent_id,
            self.parent_activite,
            self.name,
            _json_text(self.label),
        )


@dataclass(frozen=True, slots=True)
class ProjectedCriterion:
    """One of the 8 expressible criteria, named by AccesLibre's own field."""

    criterion_id: int
    field: str
    parent_id: int | None
    parent_field: str | None
    type: str
    position: int
    handicap_families: list[str]
    label: dict[str, object]
    en17210_ref: str | None

    def to_csv(self) -> tuple[object, ...]:
        return (
            self.criterion_id,
            self.field,
            self.parent_id,
            self.parent_field,
            self.type,
            self.position,
            _json_text(self.handicap_families),
            _json_text(self.label),
            self.en17210_ref,
        )


@dataclass(frozen=True, slots=True)
class ProjectedAnswer:
    """One answer keyed on a partner field name; only ``value["value"]`` leaves (V8)."""

    place_id: int
    field: str
    value: object
    source: str
    source_license: str | None
    date: datetime | None

    def to_csv(self) -> tuple[object, ...]:
        return (
            self.place_id,
            self.field,
            _json_text(self.value),
            self.source,
            self.source_license,
            "",
            _iso(self.date),
        )


@dataclass(frozen=True, slots=True)
class ProjectedAlias:
    """A merged place and its canonical place, both as partner identifiers."""

    alias_id: str
    canonical_id: str

    def to_csv(self) -> tuple[object, ...]:
        return (self.alias_id, self.canonical_id)


@dataclass(frozen=True, slots=True)
class UnmappablePlace:
    """A place the feed cannot key; ``identifier`` is kept when it existed anyway (D-05)."""

    identifier: str | None
    reason: str
    detail: str = ""

    entity = "place"

    def to_csv(self) -> tuple[object, ...]:
        return (self.entity, self.identifier, self.reason, self.detail)


@dataclass(frozen=True, slots=True)
class UnmappableAnswer:
    """An answer whose criterion has no AccesLibre field (D-08)."""

    identifier: str | None
    reason: str
    detail: str = ""

    entity = "criterion"

    def to_csv(self) -> tuple[object, ...]:
        return (self.entity, self.identifier, self.reason, self.detail)


@dataclass(frozen=True, slots=True)
class MappingRow:
    """One reviewed mapping-document row, or one diverted at export time."""

    entity: str
    identifier: str | None
    reason: str
    detail: str = ""

    def to_csv(self) -> tuple[object, ...]:
        return (self.entity, self.identifier, self.reason, self.detail)


def canonical_activites(rows: Iterable[tuple[str, str, int]]) -> dict[str, str]:
    """One ``activite`` per category slug: its largest-``places`` row (Pitfall 4, D-06).

    The inverse of ``acceslibre_categories.csv`` is not a bijection (133 slugs over 391 rows),
    so the choice is the biggest population — deterministic, and recorded in the mapping
    document. An unusable row fails closed instead of poisoning the map.
    """
    chosen: dict[str, tuple[int, str]] = {}
    for activite, category_slug, places in rows:
        if not activite.strip() or not category_slug.strip():
            raise DomainError(
                "acceslibre_categories.csv carries an empty activite or category_slug"
            )
        current = chosen.get(category_slug)
        if current is None or places > current[0]:
            chosen[category_slug] = (places, activite)
    return {slug: activite for slug, (_, activite) in chosen.items()}


def project_place(
    row: PlaceRow, activite_for: Mapping[str, str], rule: str
) -> ProjectedPlace | UnmappablePlace:
    """Key one place on their identifier and its category on their ``activite``.

    ``resolve_identifier`` returning None means "unmappable", whatever the cause: a ``blocked``
    rule, a ``slug`` rule with no ``erp_slug``, or an ``origin_id`` rule with no id. Such a row is
    never keyed on a guess — it goes to the mapping document.
    """
    identifier = resolve_identifier(rule, row.erp_slug, row.origin_id)
    if identifier is None:
        reason = "identifier_unresolved" if rule in {"blocked", "slug"} else "no_identifier"
        return UnmappablePlace(identifier=None, reason=reason, detail=f"identifier rule: {rule}")
    activite: str | None = None
    if row.category_slug is not None:
        activite = activite_for.get(row.category_slug)
        if activite is None:
            return UnmappablePlace(
                identifier=identifier,
                reason="no_category_inverse",
                detail=f"category {row.category_slug} has no canonical activite",
            )
    return ProjectedPlace(
        place_id=row.place_id,
        identifier=identifier,
        origin_id=row.origin_id,
        name=row.name,
        activite=activite,
        source_category=row.source_category,
        address_full=row.address_full,
        city=row.city,
        postal_code=row.postal_code,
        country_code=row.country_code,
        lat=row.lat,
        lng=row.lng,
        operating_status=row.operating_status,
        website=row.website,
        phone=row.phone,
        source=row.source,
        source_license=row.source_license,
        source_url=row.source_url,
        date=row.date,
    )


def project_category(row: CategoryRow, activite_for: Mapping[str, str]) -> ProjectedCategory | None:
    """The category as its canonical ``activite``; ``None`` when it has no inverse (D-06)."""
    activite = activite_for.get(row.slug)
    if activite is None:
        return None
    return ProjectedCategory(
        category_id=row.category_id,
        activite=activite,
        parent_id=row.parent_id,
        parent_activite=activite_for.get(row.parent_slug) if row.parent_slug else None,
        name=row.name,
        label=dict(row.label),
    )


def project_criterion(
    row: CriterionRow, field_for_slug: Mapping[str, str]
) -> ProjectedCriterion | None:
    """Only the 8 ``FIELD_MAP`` criteria are expressible; the rest are mapping rows (D-07)."""
    field = field_for_slug.get(row.slug)
    if field is None:
        return None
    return ProjectedCriterion(
        criterion_id=row.criterion_id,
        field=field,
        parent_id=row.parent_id,
        parent_field=field_for_slug.get(row.parent_slug) if row.parent_slug else None,
        type=row.type,
        position=row.position,
        handicap_families=list(row.handicap_families),
        label=dict(row.label),
        en17210_ref=row.en17210_ref,
    )


def project_answer(
    row: AnswerRow, field_for_slug: Mapping[str, str]
) -> ProjectedAnswer | UnmappableAnswer:
    """The answer's criterion as their field name, and only ``value["value"]`` leaves (V8)."""
    field = field_for_slug.get(row.criterion_slug)
    if field is None:
        return UnmappableAnswer(identifier=row.criterion_slug, reason="not_expressible")
    return ProjectedAnswer(
        place_id=row.place_id,
        field=field,
        value=row.value.get("value"),
        source=row.source,
        source_license=row.source_license,
        date=row.date,
    )


def project_alias(row: AliasRow, rule: str) -> ProjectedAlias | UnmappablePlace:
    """Both sides of a merge as partner identifiers; an unresolved side diverts the row."""
    alias = resolve_identifier(rule, row.alias_erp_slug, row.alias_origin_id)
    canonical = resolve_identifier(rule, row.canonical_erp_slug, row.canonical_origin_id)
    if alias is None or canonical is None:
        return UnmappablePlace(
            identifier=alias or canonical,
            reason="identifier_unresolved",
            detail=f"alias of place {row.alias_id}",
        )
    return ProjectedAlias(alias_id=alias, canonical_id=canonical)
