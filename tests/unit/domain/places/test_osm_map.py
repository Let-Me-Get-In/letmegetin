"""Unit tests for the OSM accessibility transform (pure: no osmium, no database, no settings)."""

from __future__ import annotations

import pytest

from letmegetin.domain.places.osm_map import AccessibilityMapping, accessibility_values

_MAPPING: AccessibilityMapping = {
    ("wheelchair", "yes"): ("access", "access-everywhere"),
    ("wheelchair", "limited"): ("access", "some-areas-inaccessible"),
    ("toilets:wheelchair", "no"): ("toilets", "toilets-inaccessible"),
}


def test_accessibility_values_maps_a_reviewed_pair_to_its_typed_value() -> None:
    values = accessibility_values({"wheelchair": "yes", "name": "Café du Coin"}, _MAPPING)

    assert values == {
        "access": {"value": "access-everywhere", "source": "osm", "key": "wheelchair"}
    }


def test_accessibility_values_maps_every_matching_pair() -> None:
    values = accessibility_values({"wheelchair": "limited", "toilets:wheelchair": "no"}, _MAPPING)

    assert values == {
        "access": {"value": "some-areas-inaccessible", "source": "osm", "key": "wheelchair"},
        "toilets": {"value": "toilets-inaccessible", "source": "osm", "key": "toilets:wheelchair"},
    }


@pytest.mark.parametrize(
    "tags",
    [
        {},  # no tags at all
        {"amenity": "cafe", "name": "Café"},  # no accessibility tag
        {"wheelchair": "no"},  # the review mapped no value for this one (D-06)
        {"toilets:wheelchair": "yes"},  # mapped for a different key only
    ],
)
def test_accessibility_values_drops_an_unmapped_tag(tags: dict[str, str]) -> None:
    assert accessibility_values(tags, _MAPPING) == {}


def test_accessibility_values_with_an_empty_mapping_is_empty() -> None:
    assert accessibility_values({"wheelchair": "yes"}, {}) == {}
