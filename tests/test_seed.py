"""Tests du chargeur de seed (session factice, sans base de données)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from letmegetin import seed as seed_module
from letmegetin.models import Category, CategoryCriterion, Criterion, OtherInformation

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


class _Result:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def all(self) -> list[Any]:
        return self._values


class FakeSession:
    """Fake AsyncSession recording writes; assigns ids on add."""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self._next_id = 1
        self.committed = False

    async def scalar(self, statement: Any) -> Any:
        return None

    async def scalars(self, statement: Any) -> _Result:
        return _Result([obj for obj in self.added if isinstance(obj, Category)])

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
    assert any(isinstance(obj, Category) for obj in session.added)
    assert any(isinstance(obj, OtherInformation) for obj in session.added)
    assert any(isinstance(obj, Criterion) for obj in session.added)
    assert any(isinstance(obj, CategoryCriterion) for obj in session.added)


def test_seed_has_no_schema_engine() -> None:
    assert not hasattr(seed_module, "engine")
    assert not hasattr(seed_module, "Base")
