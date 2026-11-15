"""Stream an OpenStreetMap ``.osm.pbf`` extract into :class:`OsmRow` objects.

The only module that imports ``osmium``, and it does so lazily: importing this module (and
``admin.py``, which imports it) never loads the C++ binding, so a machine without the wheel
still runs every other admin command.

shortcut: the reader is a pull generator over ``osmium.FileProcessor`` — the only shape that
streams a national extract (D-01). Never materialise it here: ``list()`` over a 4 GB France
extract is what this design exists to prevent.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.osm_map import OsmRow

MISSING_DEPENDENCY = "osmium is not installed — run `uv sync` to install the OSM import dependency"


def iter_osm_rows(path: Path) -> Iterator[OsmRow]:
    """Stream ``path`` one node/way at a time; relations carry no POI and are skipped."""
    try:
        import osmium
    except ImportError as exc:
        raise DomainError(MISSING_DEPENDENCY) from exc

    for obj in osmium.FileProcessor(str(path)).with_locations():
        if isinstance(obj, osmium.osm.Node):
            yield OsmRow(
                source_id=f"node/{obj.id}",
                name=obj.tags.get("name"),
                lat=obj.location.lat,
                lng=obj.location.lon,
                tags=dict(obj.tags),
                version=obj.version,
            )
        elif isinstance(obj, osmium.osm.Way):
            # A way imports at its first resolvable node: it has geometry but no centroid.
            lat, lng = None, None
            for ref in obj.nodes:
                try:
                    lat, lng = ref.location.lat, ref.location.lon
                except osmium.InvalidLocationError:
                    continue
                break
            yield OsmRow(
                source_id=f"way/{obj.id}",
                name=obj.tags.get("name"),
                lat=lat,
                lng=lng,
                tags=dict(obj.tags),
                version=obj.version,
            )
