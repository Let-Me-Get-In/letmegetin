"""The .osmChange 0.6 serialiser (pure: no SQLAlchemy, no osmium, no FastAPI).

An ``.osmChange`` ``<modify>`` element replaces the target object's whole tag set, so the
serialiser never curates: it emits the full, already-merged mapping it is given. A caller that
passes a partial set is the destructive case the publish gate refuses (BLOCKER 1).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from xml.sax.saxutils import escape

OSM_CHANGE_VERSION = "0.6"
GENERATOR = "letmegetin"

ACTION_MODIFY = "modify"


def _attribute(value: object) -> str:
    """A double-quoted, XML-escaped attribute value (the quote included, unlike ``escape``)."""
    return '"' + escape(str(value), {'"': "&quot;"}) + '"'


def serialize_element(
    *,
    kind: str,
    osmid: str,
    version: int,
    tags: Mapping[str, str],
    lat: float | None = None,
    lng: float | None = None,
) -> str:
    """One ``<kind>`` wrapping a ``<node>``: id, version, coordinates and every tag.

    ``tags`` is the full set to write back, never a delta: OSM replaces the whole set.
    """
    if kind != ACTION_MODIFY:
        raise ValueError(f"unsupported osmChange action {kind!r}")
    attributes = f"id={_attribute(osmid)} version={_attribute(version)}"
    if lat is not None and lng is not None:
        attributes += f" lat={_attribute(lat)} lon={_attribute(lng)}"
    lines = [f"  <{kind}>", f"    <node {attributes}>"]
    lines.extend(
        f"      <tag k={_attribute(key)} v={_attribute(value)} />" for key, value in tags.items()
    )
    lines.extend(["    </node>", f"  </{kind}>"])
    return "\n".join(lines)


def serialize_document(elements: Iterable[str]) -> str:
    """Wrap the elements in the ``osmChange`` root: one document per publish run."""
    body = "\n".join(elements)
    return (
        f'<osmChange version="{OSM_CHANGE_VERSION}" generator="{GENERATOR}">\n'
        f"{body}\n</osmChange>\n"
    )
