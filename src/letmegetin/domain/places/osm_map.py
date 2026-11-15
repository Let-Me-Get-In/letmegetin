"""The OpenStreetMap row contract the importer consumes (pure: no osmium, no SQLAlchemy).

An OSM object is imported as one place carrying the object's version and its *full raw tag
set*: an ``.osmChange`` ``<modify>`` element replaces the target object wholesale, so the
publisher can only re-emit it verbatim if it still holds every tag, mapped or not.
"""

from __future__ import annotations

from dataclasses import dataclass

SOURCE = "osm"


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
