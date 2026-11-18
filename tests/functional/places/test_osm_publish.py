"""Functional: ``osm publish`` writes one non-destructive ``.osmChange``, or nothing at all.

The two properties this file exists for are BLOCKER 1 — an emitted ``<modify>`` carries the full
tag set (stored ``osm_tags`` ∪ our accessibility tags), and a place whose stored set is absent is
refused-and-counted — and the fail-closed gate of D-10/D-11. D-09 is asserted structurally: the
publisher may not import a network client, because this phase writes a file and never uploads.
"""

from __future__ import annotations

import ast
import json
import shutil
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.application.places import osm_publish as osm_publish_module
from letmegetin.application.places.osm_publish import (
    COMMENT_NAME,
    NO_ANSWER,
    NO_STORED_TAGS,
    NO_VERSION,
    NOT_A_NODE,
    OSM_THROTTLE_SECONDS,
    OUTPUT_NAME,
    PLACEHOLDER_MARKERS,
    POLICY_ARTEFACTS,
    TOS_CONSENT,
    _licence_matrix,
    assert_publish_gate,
    load_publish_gate,
)
from letmegetin.config import settings
from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.licence import can_redistribute
from tests.db import execute, require_database, scalar, seed_source_licences
from tests.fixtures.osm_pbf import write_osm_pbf

_REFERENTIAL = Path(__file__).resolve().parents[3] / "data/referential"
_PREFIX = "test-osm-publish-"
_SLUGS = f"SELECT id FROM place WHERE slug LIKE '{_PREFIX}%'"
_CLEANUP = (
    "DELETE FROM export_event WHERE entity_id IN (SELECT id FROM place WHERE source = 'osm')",
    "DELETE FROM place_accessibility_write WHERE place_id IN "
    "(SELECT id FROM place WHERE source = 'osm')",
    "DELETE FROM place WHERE source = 'osm'",
    f"DELETE FROM place_accessibility_write WHERE place_id IN ({_SLUGS})",
    f"DELETE FROM place WHERE id IN ({_SLUGS})",
)
# The promoted gate's published wiki page; a test asserts the comment carries it verbatim.
_WIKI_URL = "https://example.invalid/wiki"

_CRITERION = "circulation-acces-en-fauteuil-a-tout-le-lieu"
_WHEELCHAIR_YES = f"{_CRITERION}-acces-en-fauteuil-possible-partout"
# What the synthetic PBF fixture carries on node/1 (tests/fixtures/osm_pbf.py).
_NODE_1_TAGS = {"amenity": "cafe", "name": "Café du Coin", "wheelchair": "yes"}
_NODE_1_MAPPED = {"wheelchair": "yes"}


@pytest.fixture
def partner_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The reviewed data and the real policy artefacts, with the gate's placeholders promoted."""
    data = tmp_path / "referential"
    data.mkdir()
    for name in ("osm_accessibility_tags.csv", "licences.csv", "licence_destinations.csv"):
        shutil.copy(_REFERENTIAL / name, data / name)
    shutil.copytree(_REFERENTIAL / "osm", data / "osm")
    _promote_gate(data / "osm")
    monkeypatch.setattr(settings, "data_dir", data)
    return data


def _promote_gate(policy: Path) -> None:
    """The three human actions the checkpoint asks for, so a happy path can run at all."""
    (policy / TOS_CONSENT).write_text("accepted\n", encoding="utf-8")
    (policy / "discussion_url.txt").write_text(
        "https://example.invalid/osm-community-thread\n", encoding="utf-8"
    )
    wiki = policy / "wiki_page.md"
    wiki.write_text(
        wiki.read_text(encoding="utf-8").replace("<to be published>", _WIKI_URL),
        encoding="utf-8",
    )


@pytest.fixture
def db(test_sessions: None) -> Iterator[None]:
    require_database("place", "place_accessibility", "criteria", "source_licence")
    _cleanup()
    yield
    _cleanup()


@pytest.fixture
def osm_licence(test_sessions: None) -> None:
    """Load the reviewed source licences (``osm;odbl``), as ``seed`` does before an import."""
    seed_source_licences()


def _cleanup() -> None:
    for statement in _CLEANUP:
        execute(statement)


def _place(
    source_id: str,
    name: str,
    *,
    osm_tags: dict[str, str] | None,
    version: int | None,
    source: str = "osm",
) -> int:
    return scalar(
        "INSERT INTO place (source, source_id, name, name_normalized, slug, lat, lng, "
        "source_license, osm_version, osm_tags) VALUES (:source, :source_id, :name, :name, :slug, "
        "45.1, 5.1, 'odbl', :version, CAST(:tags AS jsonb)) RETURNING id",
        {
            "source": source,
            "source_id": source_id,
            "name": name,
            "slug": _PREFIX + source_id.replace("/", "-"),
            "version": version,
            "tags": None if osm_tags is None else json.dumps(osm_tags, ensure_ascii=False),
        },
    )


def _answer(place_id: int, value: str, *, source: str = "user", licence: str | None = None) -> None:
    execute(
        "INSERT INTO place_accessibility (place_id, criterion_id, value, source, source_license, "
        "actor) SELECT :place_id, id, CAST(:value AS jsonb), :source, :licence, 'test' "
        "FROM criteria WHERE slug = :slug",
        {
            "place_id": place_id,
            "value": json.dumps({"value": value, "source": source}),
            "source": source,
            "licence": licence or ("dual" if source == "user" else "odbl"),
            "slug": _CRITERION,
        },
    )


def _invoke(tmp_path: Path):
    return CliRunner().invoke(admin.app, ["osm", "publish", "--out", str(tmp_path / "out")])


def _publish(tmp_path: Path) -> str:
    result = _invoke(tmp_path)
    assert result.exit_code == 0, result.output
    return result.output


def _nodes(tmp_path: Path) -> list[ET.Element]:
    document = ET.fromstring((tmp_path / "out" / OUTPUT_NAME).read_text(encoding="utf-8"))
    assert document.tag == "osmChange"
    return document.findall("./modify/node")


def _tags(node: ET.Element) -> dict[str, str]:
    return {tag.get("k", ""): tag.get("v", "") for tag in node.findall("tag")}


def test_osm_publish_emits_the_stored_tags_merged_with_the_answer(
    db: None, partner_data: Path, tmp_path: Path
) -> None:
    place_id = _place(
        "node/1",
        "Café du Coin",
        osm_tags={"amenity": "cafe", "name": "Café du Coin"},
        version=7,
    )
    # A user's answer whose tag is NOT in the stored set: the element can only carry
    # wheelchair=yes if the merge ADDS it, and can only keep amenity/name if it does not
    # replace the stored set (BLOCKER 1).
    _answer(place_id, _WHEELCHAIR_YES)
    refused = _place("node/2", "Sans tags", osm_tags=None, version=3)
    _answer(refused, _WHEELCHAIR_YES)
    way = _place("way/456", "Rue du Coin", osm_tags={"highway": "residential"}, version=2)
    _answer(way, _WHEELCHAIR_YES)

    output = _publish(tmp_path)

    assert "emitted=1 elements=1" in output
    assert f"not emitted ({NO_STORED_TAGS}): 1" in output
    assert f"not emitted ({NOT_A_NODE}): 1" in output
    # node/1 is the single object that produces the single emitted element (BLOCKER 3).
    nodes = _nodes(tmp_path)
    assert len(nodes) == 1
    node = nodes[0]
    assert node.get("id") == "1"
    assert node.get("version") == "7"
    assert node.get("lat") == "45.1"
    assert node.get("lon") == "5.1"
    assert _tags(node) == {
        "amenity": "cafe",
        "name": "Café du Coin",
        "wheelchair": "yes",
    }


def test_osm_throttle_is_a_positive_constant() -> None:
    assert OSM_THROTTLE_SECONDS > 0


@pytest.mark.parametrize("consent", ["pending", "declined", "accepted "])
def test_osm_publish_refuses_a_non_consent_flag(
    db: None, partner_data: Path, tmp_path: Path, consent: str
) -> None:
    (partner_data / "osm" / TOS_CONSENT).write_text(consent, encoding="utf-8")

    result = _invoke(tmp_path)

    assert result.exit_code == 1, result.output
    assert "terms-of-service" in result.output
    assert not (tmp_path / "out" / OUTPUT_NAME).exists()


@pytest.mark.parametrize("missing", (*POLICY_ARTEFACTS, TOS_CONSENT))
def test_osm_publish_refuses_a_missing_artefact(
    db: None, partner_data: Path, tmp_path: Path, missing: str
) -> None:
    (partner_data / "osm" / missing).unlink()

    result = _invoke(tmp_path)

    assert result.exit_code == 1, result.output
    assert missing in result.output
    assert not (tmp_path / "out" / OUTPUT_NAME).exists()
    assert not (tmp_path / "out" / COMMENT_NAME).exists()


@pytest.mark.parametrize("empty", (*POLICY_ARTEFACTS, TOS_CONSENT))
def test_osm_publish_refuses_an_empty_artefact(
    db: None, partner_data: Path, tmp_path: Path, empty: str
) -> None:
    (partner_data / "osm" / empty).write_text("", encoding="utf-8")

    result = _invoke(tmp_path)

    assert result.exit_code == 1, result.output
    assert f"{empty} is empty" in result.output
    assert not (tmp_path / "out" / OUTPUT_NAME).exists()
    assert not (tmp_path / "out" / COMMENT_NAME).exists()


@pytest.mark.parametrize(
    ("old", "new"),
    [("LetMeGetIn", "TheProject"), ("{wiki_url}", "the wiki page")],
    ids=["without-the-project-name", "without-the-wiki-placeholder"],
)
def test_osm_publish_refuses_a_template_it_cannot_render(
    db: None, partner_data: Path, tmp_path: Path, old: str, new: str
) -> None:
    template = partner_data / "osm" / "changeset_comment_template.txt"
    template.write_text(template.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    result = _invoke(tmp_path)

    assert result.exit_code == 1, result.output
    assert "changeset_comment_template.txt" in result.output
    assert not (tmp_path / "out" / OUTPUT_NAME).exists()


@pytest.mark.parametrize(
    "value",
    ["<to be published>", "http://example.invalid/thread", "https://example.invalid/TODO"],
    ids=["placeholder", "not-https", "todo-marker"],
)
def test_osm_publish_refuses_an_unpublished_discussion_url(
    db: None, partner_data: Path, tmp_path: Path, value: str
) -> None:
    (partner_data / "osm" / "discussion_url.txt").write_text(value, encoding="utf-8")

    result = _invoke(tmp_path)

    assert result.exit_code == 1, result.output
    assert "discussion_url.txt" in result.output
    assert not (tmp_path / "out" / OUTPUT_NAME).exists()


@pytest.mark.parametrize(
    "url",
    ["<to be published>", "http://example.invalid/wiki"],
    ids=["placeholder", "not-https"],
)
def test_osm_publish_refuses_an_unpublished_wiki_url(
    db: None, partner_data: Path, tmp_path: Path, url: str
) -> None:
    wiki = partner_data / "osm" / "wiki_page.md"
    wiki.write_text(wiki.read_text(encoding="utf-8").replace(_WIKI_URL, url), encoding="utf-8")

    result = _invoke(tmp_path)

    assert result.exit_code == 1, result.output
    assert "wiki page url: line" in result.output
    assert not (tmp_path / "out" / OUTPUT_NAME).exists()


def test_assert_publish_gate_refuses_a_placeholder_with_a_domain_error(
    partner_data: Path,
) -> None:
    wiki = partner_data / "osm" / "wiki_page.md"
    wiki.write_text(
        wiki.read_text(encoding="utf-8").replace(_WIKI_URL, "<to be published>"), encoding="utf-8"
    )

    with pytest.raises(DomainError):
        assert_publish_gate(load_publish_gate(partner_data))


def test_osm_publish_comment_names_the_project_and_the_real_wiki_url(
    db: None, partner_data: Path, tmp_path: Path
) -> None:
    place_id = _place("node/1", "Café du Coin", osm_tags={"amenity": "cafe"}, version=1)
    _answer(place_id, _WHEELCHAIR_YES)

    output = _publish(tmp_path)

    comment_path = tmp_path / "out" / COMMENT_NAME
    comment = comment_path.read_text(encoding="utf-8")
    assert f"changeset comment: {comment_path}" in output
    assert "LetMeGetIn" in comment
    assert _WIKI_URL in comment
    # WARNING 7: the gate refused a placeholder url: line before rendering, so none can survive.
    assert not any(marker in comment for marker in PLACEHOLDER_MARKERS)


def test_osm_publish_selects_only_answers_the_matrix_lets_leave(
    db: None, partner_data: Path, tmp_path: Path
) -> None:
    matrix = _licence_matrix(partner_data)
    assert can_redistribute("odbl", "osm", matrix)
    # D-12/LIC-03 stays a reviewed row: odbl never reaches a lov2 destination.
    assert not can_redistribute("odbl", "lov2_partner", matrix)

    osm_place = _place("node/10", "Café OSM", osm_tags={"amenity": "cafe"}, version=4)
    _answer(osm_place, _WHEELCHAIR_YES, source="osm", licence="odbl")
    # A licence the reviewed matrix does not allow towards osm: fail-closed, never emitted.
    unreviewed = _place("node/11", "Bar sans licence", osm_tags={"amenity": "bar"}, version=5)
    _answer(unreviewed, _WHEELCHAIR_YES, source="proprietary", licence="proprietary")
    # An AccesLibre place is not even scanned: only source='osm' rows can reach OSM.
    partner = _place(
        "node/12",
        "Resto partenaire",
        osm_tags={"amenity": "restaurant"},
        version=6,
        source="acceslibre",
    )
    _answer(partner, _WHEELCHAIR_YES, source="acceslibre", licence="lov2")

    output = _publish(tmp_path)

    assert "emitted=1 elements=1" in output
    assert f"not emitted ({NO_ANSWER}): 1" in output
    assert [node.get("id") for node in _nodes(tmp_path)] == ["10"]


def test_osm_publish_is_deterministic_and_skips_what_it_cannot_key(
    db: None, partner_data: Path, tmp_path: Path
) -> None:
    emitted = _place(
        "node/30", "Café du Coin", osm_tags={"amenity": "cafe", "name": "Café du Coin"}, version=9
    )
    _answer(emitted, _WHEELCHAIR_YES)
    version_less = _place("node/31", "Sans version", osm_tags={"amenity": "baker"}, version=None)
    _answer(version_less, _WHEELCHAIR_YES)
    way = _place("way/32", "Rue du Coin", osm_tags={"highway": "residential"}, version=2)
    _answer(way, _WHEELCHAIR_YES)
    tagless = _place("node/33", "Sans tags", osm_tags=None, version=3)
    _answer(tagless, _WHEELCHAIR_YES)

    output = _publish(tmp_path)
    first = (tmp_path / "out" / OUTPUT_NAME).read_bytes()
    _publish(tmp_path)
    second = (tmp_path / "out" / OUTPUT_NAME).read_bytes()

    assert first == second
    assert f"not emitted ({NO_VERSION}): 1" in output
    assert f"not emitted ({NOT_A_NODE}): 1" in output
    assert f"not emitted ({NO_STORED_TAGS}): 1" in output
    nodes = _nodes(tmp_path)
    assert [node.get("id") for node in nodes] == ["30"]
    node = nodes[0]
    assert node.get("version") == "9"
    assert node.get("lat") == "45.1"
    assert node.get("lon") == "5.1"
    assert _tags(node) == {"amenity": "cafe", "name": "Café du Coin", "wheelchair": "yes"}


def test_osm_publish_module_imports_no_network_client() -> None:
    source = Path(osm_publish_module.__file__).read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    # D-09: the publish path writes a file; wiring an uploader is a later, separate decision.
    assert imported.isdisjoint({"socket", "httpx", "requests", "aiohttp", "urllib", "osmium"})


def test_import_then_publish_emits_the_raw_tags_plus_the_mapped_answer(
    db: None, osm_licence: None, partner_data: Path, tmp_path: Path
) -> None:
    path = tmp_path / "fixture.osm.pbf"
    write_osm_pbf(path)
    imported = CliRunner().invoke(admin.app, ["import", "osm", "--file", str(path), "--no-dedup"])
    assert imported.exit_code == 0, imported.output

    output = _publish(tmp_path)

    assert "emitted=1 elements=1" in output
    nodes = _nodes(tmp_path)
    assert len(nodes) == 1
    node = nodes[0]
    assert node.get("id") == "1"
    # The fixture's object version, not a fabricated one.
    assert node.get("version") == "1"
    # The import stored the full raw tag set; publish emits it back with our answer on top,
    # so no live tag is dropped anywhere in the chain (BLOCKER 1).
    assert _tags(node) == {**_NODE_1_TAGS, **_NODE_1_MAPPED}
