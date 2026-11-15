"""Unit tests for the reviewed OSM accessibility mapping: the fail-closed loader and the audit."""

from __future__ import annotations

from pathlib import Path

import pytest

from letmegetin.application.referential.osm_tags import (
    HEADER,
    accessibility_gaps,
    audit_osm_tags,
    load_osm_accessibility_tags,
)
from letmegetin.core.exceptions import DomainError
from letmegetin.domain.referential.entities import Category, Criterion

_GOOD = (
    "osm_key;osm_value;criterion_slug;criterion_value\n"
    "wheelchair;yes;access;access-everywhere\n"
    "toilets:wheelchair;no;toilets;false\n"
)


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "osm_accessibility_tags.csv"
    path.write_text(content, encoding="utf-8")
    return path


def _criterion(
    slug: str,
    identifier: int,
    *,
    parent_id: int | None = None,
    kind: str = "option",
) -> Criterion:
    return Criterion(id=identifier, slug=slug, parent_id=parent_id, type=kind, position=0)


_CRITERIA = [
    _criterion("access", 1),
    _criterion("access-everywhere", 2, parent_id=1),
    _criterion("some-areas-inaccessible", 3, parent_id=1),
    _criterion("toilets", 4),
    _criterion("toilets-inaccessible", 5, parent_id=4),
    _criterion("ramp", 6, kind="boolean"),
]


def test_load_reads_the_reviewed_mapping(tmp_path: Path) -> None:
    mapping = load_osm_accessibility_tags(_write(tmp_path, _GOOD))

    assert mapping == {
        ("wheelchair", "yes"): ("access", "access-everywhere"),
        ("toilets:wheelchair", "no"): ("toilets", "false"),
    }


def test_load_rejects_a_wrong_header(tmp_path: Path) -> None:
    path = _write(tmp_path, "osm_tag;criterion_slug\nwheelchair;access\n")

    with pytest.raises(DomainError, match="needs the header"):
        load_osm_accessibility_tags(path)


def test_load_rejects_a_duplicate_pair(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "osm_key;osm_value;criterion_slug;criterion_value\n"
        "wheelchair;yes;access;access-everywhere\n"
        "wheelchair;yes;toilets;false\n",
    )

    with pytest.raises(DomainError, match="maps 'wheelchair=yes' twice"):
        load_osm_accessibility_tags(path)


@pytest.mark.parametrize(
    "row",
    [
        "wheelchair;;access;access-everywhere",
        "wheelchair;yes;;access-everywhere",
        "wheelchair;yes;access;",
    ],
)
def test_load_rejects_an_empty_field(tmp_path: Path, row: str) -> None:
    path = _write(tmp_path, f"{';'.join(HEADER)}\n{row}\n")

    with pytest.raises(DomainError, match="incomplete row"):
        load_osm_accessibility_tags(path)


def test_load_rejects_an_unreadable_file(tmp_path: Path) -> None:
    with pytest.raises(DomainError, match="unreadable"):
        load_osm_accessibility_tags(tmp_path / "missing.csv")


def test_accessibility_gaps_accepts_the_reviewed_values() -> None:
    mapping = {
        ("wheelchair", "yes"): ("access", "access-everywhere"),
        ("wheelchair", "limited"): ("access", "some-areas-inaccessible"),
        ("ramp", "yes"): ("ramp", "true"),
        ("toilets:wheelchair", "no"): ("toilets", "toilets-inaccessible"),
    }

    assert accessibility_gaps(_CRITERIA, mapping) == []


def test_accessibility_gaps_names_an_unknown_criterion() -> None:
    gaps = accessibility_gaps(_CRITERIA, {("wheelchair", "yes"): ("bogus", "true")})

    assert gaps == ["wheelchair=yes names unknown criterion 'bogus'"]


@pytest.mark.parametrize("value", ["yes", "1", ""])
def test_accessibility_gaps_names_an_illegal_boolean_value(value: str) -> None:
    gaps = accessibility_gaps(_CRITERIA, {("ramp", "yes"): ("ramp", value)})

    assert gaps == [f"ramp=yes maps 'ramp' to illegal boolean value '{value}'"]


def test_accessibility_gaps_names_an_option_that_is_not_a_child() -> None:
    # `some-areas-inaccessible` belongs to `access`, not to `toilets`.
    gaps = accessibility_gaps(
        _CRITERIA, {("toilets:wheelchair", "no"): ("toilets", "some-areas-inaccessible")}
    )

    assert gaps == [
        "toilets:wheelchair=no maps 'toilets' to illegal option value 'some-areas-inaccessible'"
    ]


def test_audit_osm_tags_names_an_osm_tag_resolving_to_no_category() -> None:
    gaps = audit_osm_tags(
        [Category(id=1, slug="cafe", name="Café")],
        _CRITERIA,
        {"amenity=cafe": "cafe", "shop=bakery": "bakery"},
        {},
    )

    assert gaps == ["category_mapping osm_tag 'shop=bakery' resolves to no category 'bakery'"]


def test_audit_osm_tags_names_both_kinds_of_gap() -> None:
    gaps = audit_osm_tags(
        [Category(id=1, slug="cafe", name="Café")],
        _CRITERIA,
        {"shop=bakery": "bakery"},
        {("wheelchair", "yes"): ("bogus", "true")},
    )

    assert len(gaps) == 2
