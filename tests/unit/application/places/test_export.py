"""Unit: the pure export plan — CSV shape, formula guard, manifest, remap precedence (D-02…D-06)."""

from __future__ import annotations

import asyncio
import csv
import io
from datetime import date, datetime

import pytest

from letmegetin.application.places.attribution import (
    FORWARD_LOOKING_SENTENCE,
    PRODUCED_WORKS_SENTENCE,
    render_source_line,
)
from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.export_plan import (
    ANSWERS_FILE,
    ANSWERS_HEADER,
    ATTRIBUTION_FILE,
    PLACES_FILE,
    PLACES_HEADER,
    AliasRow,
    AnswerRow,
    CategoryRow,
    CriterionRow,
    PlaceRow,
    answer_precedence,
    build_manifest,
    serialise_rows,
)
from letmegetin.domain.places.licence import can_redistribute

_MATRIX = {
    ("lov2", "open_export"): True,
    ("odbl", "open_export"): False,
}


def _place(**overrides: object) -> PlaceRow:
    fields: dict[str, object] = {
        "place_id": 1,
        "origin_id": "123",
        "slug": "un-lieu",
        "name": "Un lieu",
        "category_slug": "restaurant",
        "source_category": "restaurant",
        "address_full": "1 rue de Test, 75001 Paris",
        "city": "Paris",
        "postal_code": "75001",
        "country_code": "FR",
        "lat": 48.85,
        "lng": 2.35,
        "operating_status": "open",
        "website": None,
        "phone": None,
        "source": "acceslibre",
        "source_license": "lov2",
        "source_url": None,
        "date": datetime(2026, 11, 1, 12, 0),
    }
    fields.update(overrides)
    return PlaceRow(**fields)  # type: ignore[arg-type]


def _read_csv(payload: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(payload)))


def test_serialise_rows_round_trips_a_cell_with_a_comma_quote_and_newline() -> None:
    payload = serialise_rows(
        PLACES_HEADER,
        [_place(name='Le "Bar", côté\njardin')],
        PLACES_FILE,
    )

    rows = _read_csv(payload)

    assert rows[0] == list(PLACES_HEADER)
    assert rows[1][PLACES_HEADER.index("name")] == 'Le "Bar", côté\njardin'
    assert payload.startswith("place_id,origin_id,slug,name,")
    assert not payload.startswith("\ufeff")


def test_the_guard_neutralises_a_formula_only_in_a_free_text_column() -> None:
    payload = serialise_rows(
        PLACES_HEADER,
        [_place(name="=cmd|'/c calc'!A1", city="@SUM(1)")],
        PLACES_FILE,
    )

    row = _read_csv(payload)[1]

    assert row[PLACES_HEADER.index("name")] == "'=cmd|'/c calc'!A1"
    assert row[PLACES_HEADER.index("city")] == "'@SUM(1)"


def test_negative_coordinates_and_a_leading_plus_phone_reach_the_csv_unchanged() -> None:
    payload = serialise_rows(
        PLACES_HEADER,
        [_place(lng=-4.49, lat=-21.1, phone="+33 1 23 45 67 89")],
        PLACES_FILE,
    )

    row = _read_csv(payload)[1]

    assert row[PLACES_HEADER.index("lng")] == "-4.49"
    assert row[PLACES_HEADER.index("phone")] == "+33 1 23 45 67 89"


def test_the_guard_never_touches_the_header_row() -> None:
    payload = serialise_rows(PLACES_HEADER, [], PLACES_FILE)

    header = _read_csv(payload)[0]

    assert header == list(PLACES_HEADER)
    assert header[0] == "place_id"


def test_answers_are_keyed_by_place_and_criterion_slug_with_a_json_value() -> None:
    payload = serialise_rows(
        ANSWERS_HEADER,
        [
            AnswerRow(
                place_id=42,
                criterion_slug="entree-largeur",
                value={"value": True},
                source="acceslibre",
                source_license="lov2",
                date=datetime(2026, 5, 1, 10, 0),
            )
        ],
        ANSWERS_FILE,
    )

    row = dict(zip(ANSWERS_HEADER, _read_csv(payload)[1], strict=True))

    assert (row["place_id"], row["criterion_slug"]) == ("42", "entree-largeur")
    assert row["value"] == '{"value": true}'
    assert row["source_url"] == ""
    assert row["date"] == "2026-05-01T10:00:00+00:00"


def test_a_withheld_answer_is_absent_from_the_stream_and_counted_by_source_and_licence() -> None:
    # The place is lov2 (exportable) while some of its answers are odbl (withheld here): D-03
    # excludes the answer only, and the counter keeps the loss visible to the partner.
    answers = [
        ("acceslibre", "lov2", {"value": True}),
        ("acceslibre", "odbl", {"value": False}),
        ("acceslibre", "odbl", {"value": True}),
    ]

    exported = [answer for answer in answers if can_redistribute(answer[1], "open_export", _MATRIX)]
    excluded: dict[tuple[str, str], int] = {}
    for source, licence, _ in answers:
        if not can_redistribute(licence, "open_export", _MATRIX):
            excluded[(source, licence)] = excluded.get((source, licence), 0) + 1

    assert [answer[2] for answer in exported] == [{"value": True}]
    assert excluded == {("acceslibre", "odbl"): 2}


def test_answer_precedence_prefers_the_canonical_place_then_the_newest_then_the_highest_ids() -> (
    None
):
    canonical = answer_precedence(
        canonical_id=10, place_id=10, recorded_at=datetime(2026, 1, 1), criterion_id=5
    )
    merged_newest = answer_precedence(
        canonical_id=10, place_id=11, recorded_at=datetime(2026, 11, 1), criterion_id=5
    )
    merged_older = answer_precedence(
        canonical_id=10, place_id=11, recorded_at=datetime(2026, 2, 1), criterion_id=5
    )
    merged_same_date_lower_id = answer_precedence(
        canonical_id=10, place_id=12, recorded_at=datetime(2026, 2, 1), criterion_id=5
    )

    ranked = sorted([merged_older, canonical, merged_same_date_lower_id, merged_newest])

    # Rank 1 is the canonical answer whatever its date; then newest first; then place_id DESC.
    assert ranked == [canonical, merged_newest, merged_same_date_lower_id, merged_older]


def test_build_manifest_carries_every_key_the_contract_names() -> None:
    manifest = build_manifest(
        generated_at=datetime(2026, 11, 14, 12, 0),
        referential_version=7,
        files={PLACES_FILE: 2, ATTRIBUTION_FILE: 1},
        excluded_places=[("acceslibre", "odbl", 3)],
        excluded_answers=[("acceslibre", "odbl", 4)],
        place_withheld_answers=[("acceslibre", "odbl", 1)],
        attribution="text",
    )

    assert set(manifest) == {
        "schema_version",
        "generated_at",
        "referential_version",
        "files",
        "excluded_places",
        "excluded_answers",
        "place_withheld_answers",
        "attribution",
        "attribution_ref",
    }
    assert manifest["schema_version"] == "1.0"
    assert manifest["generated_at"] == "2026-11-14T12:00:00+00:00"
    assert manifest["excluded_answers"] == [{"source": "acceslibre", "licence": "odbl", "count": 4}]
    assert manifest["place_withheld_answers"] == [
        {"source": "acceslibre", "licence": "odbl", "count": 1}
    ]
    assert manifest["attribution_ref"] == ATTRIBUTION_FILE


def test_build_manifest_records_the_window_of_a_delta_or_catch_up() -> None:
    manifest = build_manifest(
        generated_at=datetime(2026, 11, 14, 12, 0),
        referential_version=7,
        files={},
        excluded_places=[],
        excluded_answers=[],
        place_withheld_answers=[],
        attribution="",
        mode="delta",
        from_seq=10,
        to_seq=20,
    )

    assert (manifest["mode"], manifest["from_seq"], manifest["to_seq"]) == ("delta", 10, 20)


def test_render_source_line_appends_the_reviewed_sentence_of_its_licence() -> None:
    line = render_source_line(
        "acceslibre", "Licence Ouverte v2.0 (Etalab 2.0)", date(2026, 11, 1), "« Source » : …"
    )

    assert line == ("acceslibre — Licence Ouverte v2.0 (Etalab 2.0) — 2026-11-01 — « Source » : …")


@pytest.mark.parametrize("text", [None, ""])
def test_render_source_line_omits_a_licence_sentence_it_does_not_have(text: str | None) -> None:
    line = render_source_line("acceslibre", "Licence Ouverte v2.0", None, text)

    assert line == "acceslibre — Licence Ouverte v2.0 — date unknown"
    assert "obligations" not in line


def test_the_closing_sentences_are_the_reviewed_odbl_wording() -> None:
    assert PRODUCED_WORKS_SENTENCE.startswith(
        "The API and the map are Produced Works under the ODbL"
    )
    assert FORWARD_LOOKING_SENTENCE == "Later exports may include sources not listed in this one."


def test_every_row_type_serialises_in_its_header_order() -> None:
    category = CategoryRow(
        category_id=1,
        slug="restaurant",
        parent_id=None,
        parent_slug=None,
        name="Restaurant",
        label={"fr": "Restaurant"},
    )
    criterion = CriterionRow(
        criterion_id=2,
        slug="entree-largeur",
        parent_id=None,
        parent_slug=None,
        type="boolean",
        position=0,
        handicap_families=["moteur"],
        label={"fr": "Largeur d'entrée"},
        en17210_ref=None,
    )
    alias = AliasRow(alias_id=9, canonical_id=3)

    assert category.to_csv()[0] == 1
    assert criterion.to_csv()[6] == '["moteur"]'
    assert alias.to_csv() == (9, 3)


class _EmptyMatrix:
    """An export repository whose reviewed licence matrix was never loaded."""

    async def begin_repeatable_read(self) -> None:
        return None

    async def licence_rules_count(self) -> int:
        return 0


def test_an_empty_licence_matrix_refuses_to_write_a_silently_empty_export(tmp_path) -> None:
    from letmegetin.application.places.export import export_odbl

    with pytest.raises(DomainError, match="licence matrix is empty"):
        asyncio.run(export_odbl(_EmptyMatrix(), None, out=tmp_path))  # type: ignore[arg-type]
    assert not list(tmp_path.glob("*.zip"))
