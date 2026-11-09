"""Unit tests for the place detail assembly (tree values, completion rate, reviews)."""

from __future__ import annotations

from letmegetin.application.places.get_place import get_place
from letmegetin.domain.places.entities import Place, PlaceAccessibility, PlacePhoto
from letmegetin.domain.referential.entities import CategoryGrid, Criterion


class _Places:
    def __init__(
        self,
        place: Place,
        values: list[PlaceAccessibility],
        *,
        photos: list[PlacePhoto] | None = None,
        stats: tuple[float | None, int] = (None, 0),
    ) -> None:
        self._place = place
        self._values = values
        self._photos = photos or []
        self._stats = stats

    async def get_by_slug(self, slug: str) -> Place | None:
        return self._place

    async def list_accessibility(self, place_id: int) -> list[PlaceAccessibility]:
        return self._values

    async def list_photos(self, place_id: int) -> list[PlacePhoto]:
        return self._photos

    async def review_stats(self, place_id: int) -> tuple[float | None, int]:
        return self._stats


class _Criteria:
    async def list_all(self) -> list[Criterion]:
        return [
            Criterion(
                id=1,
                slug="a",
                parent_id=None,
                type="boolean",
                position=0,
                handicap_families=["moteur"],
            ),
            Criterion(
                id=2,
                slug="b",
                parent_id=None,
                type="boolean",
                position=1,
                handicap_families=["moteur"],
            ),
        ]


class _Grids:
    def __init__(self, tree: list[dict[str, object]]) -> None:
        self._tree = tree

    async def get_for_slug(self, slug: str) -> CategoryGrid:
        return CategoryGrid(category_slug=slug, version=1, tree=self._tree)


_TREE = [
    {
        "slug": "group",
        "label": {"fr": "Groupe"},
        "type": "array",
        "children": [
            {"slug": "a", "label": {"fr": "A"}, "type": "boolean", "children": []},
            {"slug": "b", "label": {"fr": "B"}, "type": "boolean", "children": []},
        ],
    }
]


def _place(category_slug: str | None = "library") -> Place:
    return Place(
        id=1,
        name="Test",
        slug="test",
        source="test",
        category_slug=category_slug,
    )


async def test_get_place_injects_values_and_computes_filled_rate() -> None:
    detail = await get_place(
        _Places(
            _place(),
            [PlaceAccessibility(criterion_slug="a", value={"value": True})],
            photos=[PlacePhoto(url="https://example.test/a.jpg", credit="Acceslibre")],
            stats=(4.5, 2),
        ),
        _Criteria(),
        _Grids(_TREE),
        "test",
    )

    group = detail.tree[0]
    assert [child["value"] for child in group["children"]] == [{"value": True}, None]
    assert detail.filled_rate == 0.5
    assert detail.rating == 4.5
    assert detail.review_count == 2
    assert detail.photos[0].url == "https://example.test/a.jpg"


async def test_get_place_without_category_has_an_empty_tree() -> None:
    detail = await get_place(
        _Places(_place(category_slug=None), []), _Criteria(), _Grids(_TREE), "test"
    )

    assert detail.tree == []
    assert detail.filled_rate == 0.0
