"""The OpenStreetMap row contract the importer consumes (pure: no osmium, no SQLAlchemy).

An OSM object is imported as one place carrying the object's version and its *full raw tag
set*: an ``.osmChange`` ``<modify>`` element replaces the target object wholesale, so the
publisher can only re-emit it verbatim if it still holds every tag, mapped or not.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

SOURCE = "osm"

# ``(osm_key, osm_value) -> (criterion_slug, criterion_value)``, read from the reviewed
# ``osm_accessibility_tags.csv``: a tag pair the review did not map is simply absent (D-06).
AccessibilityMapping = Mapping[tuple[str, str], tuple[str, str]]


@dataclass(frozen=True, slots=True)
class OsmRow:
    """One OSM node or way, normalized to the fields the place aggregate needs."""

    # The OSM object reference, e.g. ``node/123`` / ``way/456`` (D-02).
    source_id: str
    name: str | None
    lat: float | None
    lng: float | None
    # Raw tags exactly as the PBF carried them: never trimmed, never transformed.
    tags: dict[str, str]
    # The object's version in the PBF; the OSM API needs it to address a modification.
    version: int


def accessibility_values(
    tags: Mapping[str, str],
    mapping: AccessibilityMapping,
) -> dict[str, dict[str, object]]:
    """Return ``{criterion_slug: value}`` for the reviewed tag pairs present in ``tags``.

    The mapping is reviewed data passed in, never a tag literal here (D-05), and a pair the
    review did not map is dropped rather than guessed (D-06). The value is the criterion's own
    typed value (a boolean literal or an option slug), so a consumer reads it like any answer.
    """
    values: dict[str, dict[str, object]] = {}
    for (key, value), (criterion_slug, criterion_value) in mapping.items():
        if tags.get(key) != value:
            continue
        values[criterion_slug] = {"value": criterion_value, "source": SOURCE, "key": key}
    return values
