"""Handicap-family assignment: CSV loading, inheritance, group union and audit."""

from __future__ import annotations

from pathlib import Path

import pytest

from letmegetin.application.referential.families import (
    apply_families,
    audit_families,
    load_families,
)
from letmegetin.core.exceptions import DomainError
from letmegetin.domain.referential.entities import AccessibilityFilter, Criterion


class FakeCriterionRepository:
    def __init__(self, criteria: list[Criterion]) -> None:
        self.items = {item.slug: item for item in criteria}
        self.updates: list[str] = []

    async def list_all(self) -> list[Criterion]:
        return list(self.items.values())

    async def update(self, criterion: Criterion) -> Criterion:
        self.items[criterion.slug] = criterion
        self.updates.append(criterion.slug)
        return criterion


class FakeFilterRepository:
    def __init__(self, filters: list[AccessibilityFilter]) -> None:
        self.items = {item.slug: item for item in filters}
        self.updates: list[str] = []

    async def list_all(self) -> list[AccessibilityFilter]:
        return list(self.items.values())

    async def update_families(self, filter_id: int, families: list[str]) -> None:
        for item in self.items.values():
            if item.id == filter_id:
                item.handicap_families = families
                self.updates.append(item.slug)
                return
        raise AssertionError(f"unknown filter {filter_id}")


def _criterion(
    slug: str,
    identifier: int,
    *,
    parent_id: int | None = None,
    kind: str = "boolean",
    families: list[str] | None = None,
) -> Criterion:
    return Criterion(
        id=identifier,
        slug=slug,
        parent_id=parent_id,
        type=kind,
        position=0,
        label={"fr": slug},
        handicap_families=list(families or []),
    )


def _stores() -> tuple[FakeCriterionRepository, FakeFilterRepository]:
    criteria = FakeCriterionRepository(
        [
            _criterion("entree", 1, kind="array"),
            _criterion("entree-acces", 2, parent_id=1),
            _criterion("entree-acces-rampe", 3, parent_id=2, kind="option"),
            _criterion("entree-acces-marquage", 4, parent_id=2, kind="option"),
        ]
    )
    filters = FakeFilterRepository(
        [AccessibilityFilter(id=10, slug="slope", label={"fr": "Pente"}, position=0)]
    )
    return criteria, filters


def test_load_families_orders_names_and_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "families.csv"
    path.write_text("slug;families\na;visuel|moteur\n\nb;auditif\n", encoding="utf-8")

    assert load_families(path) == {"a": ["moteur", "visuel"], "b": ["auditif"]}


@pytest.mark.parametrize(
    ("rows", "match"),
    [
        ("a;moteur\na;visuel\n", "duplicate"),
        ("a;olfactif\n", "olfactif"),
        ("a;\n", "no handicap family"),
        ("a\n", "no handicap family"),
    ],
    ids=["duplicate", "unknown-family", "empty-cell", "missing-column"],
)
def test_load_families_rejects_bad_rows(tmp_path: Path, rows: str, match: str) -> None:
    path = tmp_path / "families.csv"
    path.write_text(f"slug;families\n{rows}", encoding="utf-8")

    with pytest.raises(DomainError, match=match):
        load_families(path)


async def test_apply_families_writes_explicit_rows() -> None:
    criteria, filters = _stores()

    report = await apply_families(
        criteria, filters, {"entree-acces": ["moteur"], "slope": ["moteur"]}
    )

    assert criteria.items["entree-acces"].handicap_families == ["moteur"]
    assert filters.items["slope"].handicap_families == ["moteur"]
    assert report.criteria_updated == 1
    assert report.filters_updated == 1


async def test_options_inherit_and_an_explicit_option_wins() -> None:
    criteria, filters = _stores()

    await apply_families(
        criteria,
        filters,
        {"entree-acces": ["moteur"], "entree-acces-marquage": ["visuel"]},
    )

    assert criteria.items["entree-acces-rampe"].handicap_families == ["moteur"]
    assert criteria.items["entree-acces-marquage"].handicap_families == ["visuel"]


async def test_a_group_unions_its_children_in_canonical_order() -> None:
    criteria = FakeCriterionRepository(
        [
            _criterion("entree", 1, kind="array"),
            _criterion("entree-acces", 2, parent_id=1, families=["moteur"]),
            _criterion("entree-enseigne", 3, parent_id=1, families=["visuel", "auditif"]),
        ]
    )
    filters = FakeFilterRepository([])

    await apply_families(criteria, filters, {})

    assert criteria.items["entree"].handicap_families == ["moteur", "auditif", "visuel"]


async def test_apply_families_keeps_an_operator_value_unless_forced() -> None:
    criteria, filters = _stores()
    criteria.items["entree-acces"].handicap_families = ["mental"]

    kept = await apply_families(criteria, filters, {"entree-acces": ["moteur"]})
    assert criteria.items["entree-acces"].handicap_families == ["mental"]
    assert kept.unchanged == 1

    forced = await apply_families(criteria, filters, {"entree-acces": ["moteur"]}, overwrite=True)
    assert criteria.items["entree-acces"].handicap_families == ["moteur"]
    assert forced.criteria_updated == 1


async def test_a_second_run_writes_nothing() -> None:
    criteria, filters = _stores()
    assignments = {"entree-acces": ["moteur"], "slope": ["moteur"]}
    await apply_families(criteria, filters, assignments)
    writes = len(criteria.updates) + len(filters.updates)

    report = await apply_families(criteria, filters, assignments)

    assert len(criteria.updates) + len(filters.updates) == writes
    assert report.criteria_updated == 0
    assert report.filters_updated == 0
    assert report.inherited == 0


async def test_apply_families_rejects_an_unknown_slug() -> None:
    criteria, filters = _stores()

    with pytest.raises(DomainError, match="nope"):
        await apply_families(criteria, filters, {"nope": ["moteur"]})

    assert criteria.updates == []
    assert filters.updates == []


async def test_audit_lists_missing_criteria_then_filters() -> None:
    criteria, filters = _stores()
    filters.items["slope"].handicap_families = ["moteur"]

    assert await audit_families(criteria, filters) == [
        "entree",
        "entree-acces",
        "entree-acces-marquage",
        "entree-acces-rampe",
    ]
