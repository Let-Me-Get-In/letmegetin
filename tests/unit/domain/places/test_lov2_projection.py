"""Unit tests for the pure lov2 partner projection (no database, no socket)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.acceslibre_map import FIELD_MAP, THEIR_FIELD_FOR_SLUG
from letmegetin.domain.places.export_plan import (
    AliasRow,
    AnswerRow,
    CategoryRow,
    CriterionRow,
    PlaceRow,
)
from letmegetin.domain.places.lov2_projection import (
    LOV2_ANSWERS_HEADER,
    LOV2_CATEGORIES_HEADER,
    LOV2_CRITERIA_HEADER,
    LOV2_PLACES_HEADER,
    ProjectedAlias,
    ProjectedAnswer,
    ProjectedPlace,
    UnmappableAnswer,
    UnmappablePlace,
    canonical_activites,
    project_alias,
    project_answer,
    project_category,
    project_criterion,
    project_place,
)

_DATE = datetime(2026, 11, 1, 10, tzinfo=UTC)
_ACTIVITES = {"city_hall": "Mairie", "doctor": "Médecin"}


def _place(**overrides: object) -> PlaceRow:
    fields: dict[str, object] = {
        "place_id": 1,
        "origin_id": "origin-1",
        "slug": "notre-slug",
        "name": "Mairie de Test",
        "category_slug": "city_hall",
        "source_category": "Mairie",
        "address_full": "1 place du Test",
        "city": "Testville",
        "postal_code": "99001",
        "country_code": "FR",
        "lat": 45.1,
        "lng": 5.1,
        "operating_status": "open",
        "website": None,
        "phone": None,
        "source": "acceslibre",
        "source_license": "lov2",
        "source_url": None,
        "date": _DATE,
        "erp_slug": "mairie-de-test-12345",
    }
    fields.update(overrides)
    return PlaceRow(**fields)  # type: ignore[arg-type]


def _answer(**overrides: object) -> AnswerRow:
    fields: dict[str, object] = {
        "place_id": 1,
        "criterion_slug": "entree-acces",
        "value": {"value": "true", "source": "user", "user_id": 7},
        "source": "user",
        "source_license": "dual",
        "date": _DATE,
    }
    fields.update(overrides)
    return AnswerRow(**fields)  # type: ignore[arg-type]


def test_the_inverse_of_field_map_is_the_eight_field_names() -> None:
    assert len(FIELD_MAP) == 8
    assert {slug: field for field, slug in FIELD_MAP.items()} == THEIR_FIELD_FOR_SLUG
    assert sorted(THEIR_FIELD_FOR_SLUG.values()) == sorted(FIELD_MAP)


@pytest.mark.parametrize(
    ("rule", "expected_reason"),
    [("blocked", "identifier_unresolved"), ("slug", "identifier_unresolved")],
)
def test_a_blocked_or_slugless_rule_never_keys_a_place(rule: str, expected_reason: str) -> None:
    row = _place(erp_slug=None if rule == "slug" else "mairie-de-test-12345")

    projected = project_place(row, _ACTIVITES, rule)

    assert isinstance(projected, UnmappablePlace)
    assert projected.reason == expected_reason
    assert projected.identifier is None


def test_origin_id_rule_keys_on_the_source_id_and_never_on_our_slug() -> None:
    projected = project_place(_place(), _ACTIVITES, "origin_id")

    assert isinstance(projected, ProjectedPlace)
    assert projected.identifier == "origin-1"
    assert projected.activite == "Mairie"
    assert "notre-slug" not in projected.to_csv()


def test_slug_rule_keys_on_the_erp_slug() -> None:
    projected = project_place(_place(), _ACTIVITES, "slug")

    assert isinstance(projected, ProjectedPlace)
    assert projected.identifier == "mairie-de-test-12345"


def test_an_origin_id_rule_without_an_origin_id_is_unmappable() -> None:
    projected = project_place(_place(origin_id=None), _ACTIVITES, "origin_id")

    assert isinstance(projected, UnmappablePlace)
    assert projected.reason == "no_identifier"


def test_a_category_without_an_inverse_diverts_the_place() -> None:
    projected = project_place(_place(category_slug="unknown"), _ACTIVITES, "origin_id")

    assert isinstance(projected, UnmappablePlace)
    assert projected.reason == "no_category_inverse"
    assert projected.identifier == "origin-1"


def test_a_place_without_a_category_still_projects() -> None:
    projected = project_place(_place(category_slug=None), _ACTIVITES, "origin_id")

    assert isinstance(projected, ProjectedPlace)
    assert projected.activite is None


def test_canonical_activites_picks_the_largest_population() -> None:
    activites = canonical_activites(
        [("Médecin", "doctor", 30), ("Ostéopathe", "doctor", 3), ("Mairie", "city_hall", 1)]
    )

    assert activites == {"doctor": "Médecin", "city_hall": "Mairie"}


@pytest.mark.parametrize(("activite", "slug"), [("", "doctor"), ("Médecin", "")])
def test_canonical_activites_fails_closed_on_an_unusable_row(activite: str, slug: str) -> None:
    with pytest.raises(DomainError):
        canonical_activites([(activite, slug, 3)])


@pytest.mark.parametrize("slug", sorted(FIELD_MAP.values()))
def test_every_mapped_criterion_projects_to_its_field_name(slug: str) -> None:
    projected = project_answer(_answer(criterion_slug=slug), THEIR_FIELD_FOR_SLUG)

    assert isinstance(projected, ProjectedAnswer)
    assert projected.field == THEIR_FIELD_FOR_SLUG[slug]


def test_an_answer_outside_field_map_is_not_expressible() -> None:
    projected = project_answer(
        _answer(criterion_slug="entree-acces-avec-rampe"), THEIR_FIELD_FOR_SLUG
    )

    assert isinstance(projected, UnmappableAnswer)
    assert projected.reason == "not_expressible"
    assert projected.identifier == "entree-acces-avec-rampe"


def test_a_projected_answer_carries_only_the_value() -> None:
    projected = project_answer(_answer(), THEIR_FIELD_FOR_SLUG)

    assert isinstance(projected, ProjectedAnswer)
    assert projected.value == "true"
    assert projected.to_csv() == (
        1,
        "entree_pmr",
        '"true"',
        "user",
        "dual",
        "",
        "2026-11-01T10:00:00+00:00",
    )


def test_project_category_and_criterion_replace_our_slugs() -> None:
    category = project_category(
        CategoryRow(
            category_id=3,
            slug="city_hall",
            parent_id=None,
            parent_slug=None,
            name="Mairie",
            label={"fr": "Mairie"},
        ),
        _ACTIVITES,
    )
    criterion = project_criterion(
        CriterionRow(
            criterion_id=9,
            slug="entree-acces",
            parent_id=2,
            parent_slug="entree",
            type="boolean",
            position=1,
            handicap_families=["moteur"],
            label={"fr": "Entrée accessible"},
            en17210_ref=None,
        ),
        THEIR_FIELD_FOR_SLUG,
    )
    unknown = project_category(CategoryRow(4, "unknown", None, None, "Unknown", {}), _ACTIVITES)

    assert category is not None and category.activite == "Mairie"
    assert criterion is not None and criterion.field == "entree_pmr"
    assert criterion.parent_field is None
    assert unknown is None


def test_project_alias_resolves_both_sides() -> None:
    row = AliasRow(
        alias_id=2,
        canonical_id=1,
        alias_origin_id="origin-2",
        canonical_origin_id="origin-1",
    )

    projected = project_alias(row, "origin_id")

    assert isinstance(projected, ProjectedAlias)
    assert (projected.alias_id, projected.canonical_id) == ("origin-2", "origin-1")


def test_project_alias_diverts_when_an_identifier_is_unresolved() -> None:
    row = AliasRow(alias_id=2, canonical_id=1, alias_origin_id="origin-2")

    projected = project_alias(row, "origin_id")

    assert isinstance(projected, UnmappablePlace)
    assert projected.reason == "identifier_unresolved"


@pytest.mark.parametrize(
    ("row", "header"),
    [
        (lambda: project_place(_place(), _ACTIVITES, "origin_id"), LOV2_PLACES_HEADER),
        (lambda: project_answer(_answer(), THEIR_FIELD_FOR_SLUG), LOV2_ANSWERS_HEADER),
    ],
)
def test_projected_rows_line_up_with_their_header(row, header) -> None:
    projected = row()

    assert len(projected.to_csv()) == len(header)


def test_the_partner_headers_name_no_internal_slug() -> None:
    forbidden = {"slug", "category_slug", "criterion_slug"}
    for header in (LOV2_PLACES_HEADER, LOV2_CATEGORIES_HEADER, LOV2_CRITERIA_HEADER):
        assert forbidden.isdisjoint(header)
    assert "criterion_slug" not in LOV2_ANSWERS_HEADER
