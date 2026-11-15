"""Generate the ``.osmChange`` an operator uploads — never an upload (D-09).

The publish path writes one file and opens no network connection: OSM's automated-edit policy
requires a human to review and send the changeset, so this module produces the document and the
gate that must be satisfied before it may exist.

Non-destructive by construction (BLOCKER 1): a ``.osmChange`` ``<modify>`` element replaces the
target object's whole tag set, so every element carries the *stored* ``osm_tags`` merged with the
accessibility tags our reviewed mapping writes back. A place whose stored tag set is absent is
refused and counted, never emitted with a partial set: that would delete every live tag the
element omits.

The gate is fail-closed (D-10, D-11): the five policy artefacts and an explicit ``accepted``
terms-of-service flag must be present under ``<data_dir>/osm/`` before anything is written.
16-05 authors those artefacts; this module only refuses to run without them.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from letmegetin.application.referential.osm_tags import load_osm_accessibility_tags
from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.entities import Place, PlaceAccessibility
from letmegetin.domain.places.osm_change import ACTION_MODIFY, serialize_document, serialize_element
from letmegetin.domain.places.osm_map import SOURCE, AccessibilityMapping
from letmegetin.domain.places.repositories import PlaceRepository

# No OSM quota is published, so this is the operator-adjustable seam the future uploader reads
# (D-10, BLOCKER 4). Nothing in this phase sleeps on it: the generator writes a file.
OSM_THROTTLE_SECONDS = 5.0

# ``changeset_comment_template.txt`` is a gate artefact too, but the generator writes only the
# .osmChange; 16-05 owns the comment rendering.
POLICY_ARTEFACTS = (
    "import_plan.md",
    "wiki_page.md",
    "discussion_url.txt",
    "changeset_comment_template.txt",
    "bot_account.md",
)
TOS_CONSENT = "tos_consent.txt"
CONSENT_ACCEPTED = "accepted"

OUTPUT_NAME = "answers.osmChange"

# Why a selected place produced no element. Stable strings: the report prints them verbatim.
NO_ANSWER = "no reviewed accessibility answer to publish"
NO_STORED_TAGS = "no stored osm_tags (a partial modify would delete live tags)"
NO_VERSION = "no osm_version"
NOT_A_NODE = "not a node/<id> object"
NO_COORDINATES = "no coordinates"


@dataclass
class OsmPublishReport:
    """What one ``osm publish`` run did, for the CLI to print."""

    emitted: int = 0
    element_count: int = 0
    not_emitted: dict[str, int] = field(default_factory=dict)


def format_publish_report(report: OsmPublishReport) -> list[str]:
    lines = [f"osm publish: emitted={report.emitted} elements={report.element_count}"]
    lines.extend(
        f"  not emitted ({reason}): {count}" for reason, count in sorted(report.not_emitted.items())
    )
    return lines


def _require_policy(data_dir: Path) -> None:
    """Refuse to write until every artefact OSM's policy asks for is present (D-10, D-11)."""
    osm_dir = data_dir / "osm"
    missing = [name for name in (*POLICY_ARTEFACTS, TOS_CONSENT) if not (osm_dir / name).is_file()]
    if missing:
        raise DomainError(
            f"osm publish refused: {osm_dir} is missing {', '.join(missing)}; OSM's automated-edit "
            "policy requires every artefact before a changeset may be generated (D-10)"
        )
    try:
        consent = (osm_dir / TOS_CONSENT).read_text(encoding="utf-8").rstrip("\r\n")
    except OSError as exc:
        raise DomainError(f"{osm_dir / TOS_CONSENT} is unreadable: {exc}") from exc
    if consent != CONSENT_ACCEPTED:
        raise DomainError(
            f"osm publish refused: {osm_dir / TOS_CONSENT} must read '{CONSENT_ACCEPTED}', not "
            f"'{consent}'; publishing requires terms-of-service consent the user granted (D-11)"
        )


def _invert(mapping: AccessibilityMapping) -> dict[tuple[str, str], tuple[str, str]]:
    """``(criterion_slug, criterion_value) -> (osm_key, osm_value)``: the write-back direction."""
    return {
        (criterion_slug, criterion_value): (osm_key, osm_value)
        for (osm_key, osm_value), (criterion_slug, criterion_value) in mapping.items()
    }


def _mapped_tags(
    answers: Iterable[PlaceAccessibility],
    inverse: Mapping[tuple[str, str], tuple[str, str]],
) -> dict[str, str]:
    """The accessibility answers a reviewed inverse mapping can express as OSM tags."""
    tags: dict[str, str] = {}
    for answer in answers:
        value = answer.value.get("value") if isinstance(answer.value, dict) else None
        if not isinstance(value, str):
            continue
        pair = inverse.get((answer.criterion_slug, value))
        if pair is not None:
            tags[pair[0]] = pair[1]
    return tags


def _node_id(source_id: str | None) -> str | None:
    """The numeric part of ``node/<id>``; a way, a relation or a foreign id yields ``None``."""
    kind, _, identifier = (source_id or "").partition("/")
    return identifier if kind == "node" and identifier.isdigit() else None


def _refusal(place: Place, mapped: Mapping[str, str], osmid: str | None) -> str | None:
    """Why this place cannot produce a ``<modify>`` element, or ``None`` when it can."""
    if not mapped:
        return NO_ANSWER
    if place.osm_tags is None:
        # BLOCKER 1: a <modify> replaces the whole tag set, so a missing stored set is fatal.
        return NO_STORED_TAGS
    if place.osm_version is None:
        return NO_VERSION
    if osmid is None:
        return NOT_A_NODE
    if place.lat is None or place.lng is None:
        return NO_COORDINATES
    return None


def _write_atomic(path: Path, payload: bytes) -> None:
    """temp file + fsync + ``os.replace``: a reader never sees a half-written .osmChange."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


async def osm_publish(places: PlaceRepository, *, out: Path, data_dir: Path) -> OsmPublishReport:
    """Write ``answers.osmChange`` for every OSM place we hold an answer for (D-09).

    Elements are ordered by numeric object id, so two runs over the same data produce the same
    document. The file is written even when nothing is emitted: an empty ``osmChange`` is a
    valid, reviewable answer, and the gate is what decides whether it may exist at all.

    ``shortcut:`` the licence matrix is not re-read here — every reviewed source is allowed to
    the ``osm`` destination (``licence_destinations.csv``), and only ``source='osm'`` places are
    emitted. Re-check with ``can_redistribute`` when a source is added that OSM may not receive.
    """
    _require_policy(data_dir)
    accessibility = load_osm_accessibility_tags(data_dir / "osm_accessibility_tags.csv")
    inverse = _invert(accessibility)

    places_of_source = await places.list_by_source(SOURCE)
    answers = await places.list_accessibility_for_places([place.id for place in places_of_source])

    report = OsmPublishReport()
    elements: list[tuple[int, str]] = []
    for place in places_of_source:
        mapped = _mapped_tags(answers.get(place.id, ()), inverse)
        osmid = _node_id(place.source_id)
        reason = _refusal(place, mapped, osmid)
        if reason is not None:
            report.not_emitted[reason] = report.not_emitted.get(reason, 0) + 1
            continue
        # Every value above is non-None once _refusal returned None; the tuple keeps mypy honest.
        assert osmid is not None and place.osm_tags is not None and place.osm_version is not None
        assert place.lat is not None and place.lng is not None
        tags = {**place.osm_tags, **mapped}
        elements.append(
            (
                int(osmid),
                serialize_element(
                    kind=ACTION_MODIFY,
                    osmid=osmid,
                    version=place.osm_version,
                    tags=tags,
                    lat=place.lat,
                    lng=place.lng,
                ),
            )
        )
        report.emitted += 1

    elements.sort(key=lambda item: item[0])
    _write_atomic(
        out / OUTPUT_NAME,
        serialize_document(element for _, element in elements).encode("utf-8"),
    )
    report.element_count = len(elements)
    return report
