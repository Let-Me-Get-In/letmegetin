"""Build a synthetic ``.osm.pbf`` for the OSM tests (dev/test only, committed as source).

A generated file exercises the real ``osmium`` parser end to end without vendoring a 4 GB
national extract, and commits no opaque binary.

Exactly three objects, and node/1 is the single object that produces a place row (16-01) and
the single emitted ``<modify>`` element (16-04):

- node/1 — ``amenity=cafe``, named, wheelchair-tagged: the one mapped POI.
- node/2 — ``shop=antiques``, named: no reviewed category, skipped-and-counted.
- way/100 — ``highway=residential``: no reviewed category, exercises the way → point path.
"""

from __future__ import annotations

from pathlib import Path

import osmium
from osmium.osm.mutable import Node, Way

_TAGS_NODE_1 = {"amenity": "cafe", "name": "Café du Coin", "wheelchair": "yes"}
_TAGS_NODE_2 = {"shop": "antiques", "name": "Antiquités"}
_TAGS_WAY_100 = {"highway": "residential"}


def write_osm_pbf(path: Path) -> None:
    """Write the three-object fixture to ``path`` (overwriting it)."""
    path.unlink(missing_ok=True)
    with osmium.SimpleWriter(str(path)) as writer:
        writer.add_node(Node(id=1, version=1, location=(5.1, 45.1), tags=_TAGS_NODE_1))
        writer.add_node(Node(id=2, version=1, location=(5.2, 45.2), tags=_TAGS_NODE_2))
        # The way's geometry nodes: unnamed and untagged, so they import as nothing.
        writer.add_node(Node(id=10, version=1, location=(5.3, 45.3)))
        writer.add_node(Node(id=11, version=1, location=(5.4, 45.4)))
        writer.add_way(Way(id=100, version=1, nodes=[10, 11], tags=_TAGS_WAY_100))
