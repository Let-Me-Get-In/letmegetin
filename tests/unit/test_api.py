"""Route-level tests using a fake async session (no database)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from letmegetin.core.db import get_session
from letmegetin.infrastructure.persistence.models import (
    AccessibilityFilterModel,
    CategoryCriterionModel,
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
            scalars_queue=[
                _Result([root, child]),
                _Result([CategoryCriterionModel(category_id=1, criterion_id=2, excluded=False)]),
            ],
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


_FIVE_LOCALES = {
    "fr": "Restaurant",
    "en": "Restaurant",
    "es": "Restaurante",
    "de": "Restaurant",
    "it": "Ristorante",
}


def _categories_session() -> FakeSession:
    return FakeSession(
        scalars_queue=[
            _Result([CategoryModel(slug="restaurant", name="Restaurant", label=_FIVE_LOCALES)])
        ]
    )


def _filters_session() -> FakeSession:
    return FakeSession(
        scalars_queue=[
            _Result([AccessibilityFilterModel(slug="slope", label=_FIVE_LOCALES, position=3)])
        ]
    )


def _other_information_session() -> FakeSession:
    return FakeSession(
        scalars_queue=[
            _Result([OtherInformationModel(slug="th", name="th", label=_FIVE_LOCALES, link=None)])
        ]
    )


def _criteria_session() -> FakeSession:
    root = CriterionModel(
        id=1,
        slug="entree",
        parent_id=None,
        type="array",
        position=0,
        label=_FIVE_LOCALES,
        description={},
    )
    return FakeSession(
        scalar_queue=[CategoryModel(id=1, slug="restaurant", name="Restaurant", label={})],
        scalars_queue=[
            _Result([root]),
            _Result([CategoryCriterionModel(category_id=1, criterion_id=1, excluded=False)]),
        ],
    )


@pytest.mark.parametrize(
    ("path", "session_factory"),
    [
        ("/api/v1/categories", _categories_session),
        ("/api/v1/categories/restaurant/criteria", _criteria_session),
        ("/api/v1/filters", _filters_session),
        ("/api/v1/other-information", _other_information_session),
    ],
    ids=["categories", "criteria", "filters", "other-information"],
)
def test_endpoints_return_full_label_maps(
    client: TestClient, path: str, session_factory: Any
) -> None:
    _use(session_factory())

    response = client.get(path)

    assert response.status_code == 200
    assert response.json()[0]["label"] == _FIVE_LOCALES


def test_criteria_tree_exposes_description_and_option_nodes(client: TestClient) -> None:
    root = CriterionModel(
        id=1,
        slug="entree",
        parent_id=None,
        type="array",
        position=0,
        label=_FIVE_LOCALES,
        description={},
    )
    child = CriterionModel(
        id=2,
        slug="entree-acces",
        parent_id=1,
        type="boolean",
        position=1,
        label=_FIVE_LOCALES,
        description=_FIVE_LOCALES,
    )
    option = CriterionModel(
        id=3,
        slug="entree-acces-plain-pied",
        parent_id=2,
        type="option",
        position=0,
        label=_FIVE_LOCALES,
        description={"fr": "Accès de plain-pied"},
    )
    _use(
        FakeSession(
            scalar_queue=[CategoryModel(id=1, slug="restaurant", name="Restaurant", label={})],
            scalars_queue=[
                _Result([root, child, option]),
                _Result([CategoryCriterionModel(category_id=1, criterion_id=2, excluded=False)]),
            ],
        )
    )

    response = client.get("/api/v1/categories/restaurant/criteria")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["label"] == _FIVE_LOCALES
    assert body[0]["children"][0]["description"] == _FIVE_LOCALES
    assert body[0]["children"][0]["children"][0]["slug"] == "entree-acces-plain-pied"
    assert body[0]["children"][0]["children"][0]["label"] == _FIVE_LOCALES


def test_filters_keep_their_position(client: TestClient) -> None:
    _use(_filters_session())

    response = client.get("/api/v1/filters")

    assert response.json()[0]["position"] == 3
