"""Route-level tests using a fake async session (no database)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from letmegetin.core.db import get_session
from letmegetin.infrastructure.persistence.models import (
    AccessibilityFilterModel,
    CategoryModel,
    CriterionModel,
    OtherInformationModel,
)
from letmegetin.main import app


class _Result:
    def __init__(self, values: Iterable[Any]) -> None:
        self._values = list(values)

    def all(self) -> list[Any]:
        return self._values


class FakeSession:
    """Minimal AsyncSession stand-in driven by queued results."""

    def __init__(
        self,
        *,
        scalars_queue: list[_Result] | None = None,
        scalar_queue: list[Any] | None = None,
    ) -> None:
        self._scalars = list(scalars_queue or [])
        self._scalar = list(scalar_queue or [])

    async def scalars(self, statement: Any) -> _Result:
        return self._scalars.pop(0) if self._scalars else _Result([])

    async def scalar(self, statement: Any) -> Any:
        return self._scalar.pop(0) if self._scalar else None


@pytest.fixture
def client() -> Iterable[TestClient]:
    yield TestClient(app)
    app.dependency_overrides.clear()


def _use(session: FakeSession) -> None:
    async def override() -> AsyncIterator[FakeSession]:
        yield session

    app.dependency_overrides[get_session] = override


def test_list_categories(client: TestClient) -> None:
    category = CategoryModel(slug="restaurant", name="Restaurant", label={"fr": "Restaurant"})
    _use(FakeSession(scalars_queue=[_Result([category])]))
    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    assert response.json()[0]["slug"] == "restaurant"


def test_category_criteria_tree(client: TestClient) -> None:
    root = CriterionModel(
        id=1,
        slug="entree",
        parent_id=None,
        type="array",
        position=0,
        label={"fr": "Entrée"},
        description={},
    )
    child = CriterionModel(
        id=2,
        slug="entree-acces",
        parent_id=1,
        type="option",
        position=0,
        label={"fr": "Accès"},
        description={},
    )
    _use(
        FakeSession(
            scalar_queue=[CategoryModel(id=1, slug="restaurant", name="Restaurant", label={})],
            scalars_queue=[_Result([2]), _Result([root, child])],
        )
    )
    response = client.get("/api/v1/categories/restaurant/criteria")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["slug"] == "entree"
    assert body[0]["children"][0]["slug"] == "entree-acces"


def test_category_criteria_missing_category(client: TestClient) -> None:
    _use(FakeSession(scalar_queue=[None]))
    response = client.get("/api/v1/categories/unknown/criteria")
    assert response.status_code == 404


def test_list_filters(client: TestClient) -> None:
    _use(
        FakeSession(
            scalars_queue=[
                _Result([AccessibilityFilterModel(slug="slope", label={"fr": "Pente"}, position=0)])
            ]
        )
    )
    response = client.get("/api/v1/filters")
    assert response.status_code == 200
    assert response.json()[0]["slug"] == "slope"


def test_list_other_information(client: TestClient) -> None:
    _use(
        FakeSession(
            scalars_queue=[
                _Result(
                    [OtherInformationModel(slug="th", name="th", label={"fr": "TH"}, link=None)]
                )
            ]
        )
    )
    response = client.get("/api/v1/other-information")
    assert response.status_code == 200
    assert response.json()[0]["name"] == "th"
