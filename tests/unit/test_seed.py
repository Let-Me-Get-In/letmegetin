"""Seed loader tests (fake session, no database)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from letmegetin import seed as seed_module
from letmegetin.infrastructure.persistence.models import (
    CategoryCriterionModel,
    CategoryModel,
    CriterionModel,
    CriterionVocabularyModel,
    OtherInformationModel,
)

_GRID = [
    {
        "name": "ENTRÉE",
        "criteria": [
            {
                "name": "Accès",
                "description": "Comment entrer",
                "type": "multichoice",
                "options": [{"value": "Plain-pied", "label": "Accès de plain-pied"}],
            },
            {
                "name": "Hauteur (cm)",
                "type": "user_value",
                "options": [],
            },
        ],
    }
]

_VOCABULARY = [
    {
        "slug": "lecteur-de-carte",
        "label": {"fr": "Lecteur de carte", "it": "Lettore di carta"},
        "description": {},
    },
    {
        "slug": "rampe-amovible",
        "label": {"fr": "Rampe amovible"},
        "description": {"fr": "Une rampe"},
    },
]


class _Result:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def all(self) -> list[Any]:
        return self._values


class FakeSession:
    """Fake AsyncSession recording writes; assigns ids on add and answers lookups by slug."""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self._next_id = 1
        self.committed = False

    async def scalar(self, statement: Any) -> Any:
        entity = statement.column_descriptions[0].get("entity")
        compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
        for obj in self.added:
            slug = getattr(obj, "slug", None)
            if isinstance(obj, entity) and slug and f"'{slug}'" in compiled:
                return obj
        return None

    async def scalars(self, statement: Any) -> _Result:
        return _Result([obj for obj in self.added if isinstance(obj, CategoryModel)])

    def add(self, obj: Any) -> None:
        if getattr(obj, "id", None) is None:
            obj.id = self._next_id
            self._next_id += 1
        self.added.append(obj)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


class FakeSessionFactory:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    def __call__(self) -> FakeSessionFactory:
        return self

    async def __aenter__(self) -> FakeSession:
        return self._session

    async def __aexit__(self, *exc: object) -> bool:
        return False


@pytest.fixture(autouse=True)
def _skip_grids(monkeypatch: pytest.MonkeyPatch) -> None:
    """Grid precomputation needs PostGIS upserts; it is covered by the integration tests."""

    async def noop(*args: Any, **kwargs: Any) -> int:
        return 1

    monkeypatch.setattr(seed_module, "rebuild_category_grids", noop)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"type": "user_value", "name": "Hauteur (cm)"}, "integer"),
        ({"type": "user_value", "name": "Largeur"}, "string"),
        ({"options": [{"value": "a"}]}, "option"),
        ({}, "boolean"),
    ],
    ids=["user-value-cm", "user-value-string", "with-options", "empty"],
)
def test_criterion_type(data: dict[str, Any], expected: str) -> None:
    assert seed_module._criterion_type(data) == expected


def _write_data_dir(tmp_path: Path) -> Path:
    data_dir = tmp_path / "referential"
    (data_dir / "category_grids").mkdir(parents=True)
    (data_dir / "categories.json").write_text(
        json.dumps([{"slug": "restaurant", "name": "Restaurant", "label": {"fr": "Restaurant"}}]),
        encoding="utf-8",
    )
    (data_dir / "filters.json").write_text(
        json.dumps([{"slug": "slope", "label": {"fr": "Pente"}}]), encoding="utf-8"
    )
    (data_dir / "th.json").write_text(
        json.dumps([{"slug": "th", "name": "th", "label": {"fr": "Tourisme"}}]), encoding="utf-8"
    )
    (data_dir / "criteria.json").write_text(json.dumps(_VOCABULARY), encoding="utf-8")
    (data_dir / "category_grids" / "category-1.json").write_text(
        json.dumps(_GRID), encoding="utf-8"
    )
    return data_dir


async def test_seed_loads_data_without_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = FakeSession()
    monkeypatch.setattr(seed_module, "SessionLocal", FakeSessionFactory(session))
    monkeypatch.setattr(seed_module.settings, "data_dir", _write_data_dir(tmp_path))

    await seed_module.seed()

    assert session.committed
    assert any(isinstance(obj, CategoryModel) for obj in session.added)
    assert any(isinstance(obj, OtherInformationModel) for obj in session.added)
    assert any(isinstance(obj, CriterionModel) for obj in session.added)


async def test_seed_imports_the_vocabulary_without_polluting_criteria(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = FakeSession()
    monkeypatch.setattr(seed_module, "SessionLocal", FakeSessionFactory(session))
    monkeypatch.setattr(seed_module.settings, "data_dir", _write_data_dir(tmp_path))

    await seed_module.seed()

    vocabulary = [obj for obj in session.added if isinstance(obj, CriterionVocabularyModel)]
    assert {entry.slug for entry in vocabulary} == {entry["slug"] for entry in _VOCABULARY}
    criterion_slugs = {obj.slug for obj in session.added if isinstance(obj, CriterionModel)}
    assert criterion_slugs.isdisjoint({entry["slug"] for entry in _VOCABULARY})


async def test_seed_marks_only_the_grid_criteria_as_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = FakeSession()
    monkeypatch.setattr(seed_module, "SessionLocal", FakeSessionFactory(session))
    monkeypatch.setattr(seed_module.settings, "data_dir", _write_data_dir(tmp_path))

    await seed_module.seed()

    defaults = {
        obj.slug: obj.is_default for obj in session.added if isinstance(obj, CriterionModel)
    }
    assert defaults["entree-acces"] is True
    assert defaults["entree-hauteur-cm"] is True
    assert defaults["entree"] is False
    assert defaults["entree-acces-acces-de-plain-pied"] is False


async def test_seed_no_longer_materializes_category_criteria(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = FakeSession()
    monkeypatch.setattr(seed_module, "SessionLocal", FakeSessionFactory(session))
    monkeypatch.setattr(seed_module.settings, "data_dir", _write_data_dir(tmp_path))

    await seed_module.seed()

    assert not any(isinstance(obj, CategoryCriterionModel) for obj in session.added)


async def test_second_seed_adds_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    monkeypatch.setattr(seed_module, "SessionLocal", FakeSessionFactory(session))
    monkeypatch.setattr(seed_module.settings, "data_dir", _write_data_dir(tmp_path))

    await seed_module.seed()
    first_count = len(session.added)

    await seed_module.seed()

    assert len(session.added) == first_count


def test_seed_has_no_schema_engine() -> None:
    assert not hasattr(seed_module, "engine")
    assert not hasattr(seed_module, "Base")
