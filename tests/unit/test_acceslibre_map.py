"""Unit tests for the Acceslibre accessibility mapping."""

from __future__ import annotations

import pytest

from letmegetin.domain.places.acceslibre_map import FIELD_MAP, accessibility_values


@pytest.mark.parametrize("key", list(FIELD_MAP))
def test_accessibility_values_maps_known_columns(key: str) -> None:
    values = accessibility_values({key: 1})

    assert values == {FIELD_MAP[key]: {"value": 1, "source": "acceslibre", "key": key}}


@pytest.mark.parametrize("raw", [None, ""])
def test_accessibility_values_skips_empty_columns(raw: object) -> None:
    assert accessibility_values({"acces_entree": raw}) == {}


def test_accessibility_values_keeps_a_false_answer() -> None:
    values = accessibility_values({"acces_entree": False})

    assert values["entree-acces"]["value"] is False


def test_accessibility_values_ignores_unknown_columns() -> None:
    assert accessibility_values({"unknown_column": "x"}) == {}
