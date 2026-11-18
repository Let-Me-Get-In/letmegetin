"""Unit: the pure .osmChange serialiser (no database, no osmium, no network)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from letmegetin.domain.places.osm_change import serialize_document, serialize_element


def _parse(payload: str) -> ET.Element:
    return ET.fromstring(payload)


def test_serialize_element_emits_a_modify_node_with_the_full_tag_set() -> None:
    element = serialize_element(
        kind="modify",
        osmid="1",
        version=7,
        tags={"amenity": "cafe", "wheelchair": "yes"},
        lat=1.0,
        lng=2.0,
    )

    root = _parse(serialize_document([element]))

    assert root.tag == "osmChange"
    assert root.attrib == {"version": "0.6", "generator": "letmegetin"}
    modify = root.find("modify")
    assert modify is not None
    assert modify.attrib == {}
    node = modify.find("node")
    assert node is not None
    assert node.attrib == {"id": "1", "version": "7", "lat": "1.0", "lon": "2.0"}
    assert {tag.get("k"): tag.get("v") for tag in node.findall("tag")} == {
        "amenity": "cafe",
        "wheelchair": "yes",
    }


def test_serialize_element_escapes_tag_keys_and_values() -> None:
    element = serialize_element(
        kind="modify",
        osmid="1",
        version=1,
        tags={"note": 'A & B <c> "quoted"'},
        lat=0.0,
        lng=0.0,
    )

    root = _parse(serialize_document([element]))

    tag = root.find("./modify/node/tag")
    assert tag is not None
    assert tag.get("v") == 'A & B <c> "quoted"'
    assert "&amp;" in element
    assert "&lt;" in element
