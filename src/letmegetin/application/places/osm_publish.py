"""Generate the ``.osmChange`` and changeset comment an operator uploads — never an upload (D-09).

The publish path writes two files and opens no network connection: OSM's automated-edit policy
requires a human to review and send the changeset, so this module produces the document, the
changeset comment that points reviewers at the wiki page, and the gate that must be satisfied
before either may exist.

Non-destructive by construction (BLOCKER 1): a ``.osmChange`` ``<modify>`` element replaces the
target object's whole tag set, so every element carries the *stored* ``osm_tags`` merged with the
accessibility tags our reviewed mapping writes back. A place whose stored tag set is absent is
refused and counted, never emitted with a partial set: that would delete every live tag the
element omits.

The gate is fail-closed and content-aware (D-10, D-11): the five policy artefacts and an explicit
``accepted`` terms-of-service flag must be present under ``<data_dir>/osm/``, the comment template
must name the project and carry ``{wiki_url}``, and both the discussion URL and the wiki page's
``url:`` line must be real ``https://`` values, before anything is written. Consent is a human
action: this module never infers it.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from letmegetin.application.referential.licences import (
    load_licence_destinations,
    load_licences,
)
from letmegetin.application.referential.osm_tags import load_osm_accessibility_tags
from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.entities import Place, PlaceAccessibility
from letmegetin.domain.places.licence import can_redistribute
from letmegetin.domain.places.osm_change import ACTION_MODIFY, serialize_document, serialize_element
from letmegetin.domain.places.osm_map import SOURCE, AccessibilityMapping
from letmegetin.domain.places.repositories import PlaceRepository

# No OSM quota is published, so this is the operator-adjustable seam the future uploader reads
# (D-10, BLOCKER 4). Nothing in this phase sleeps on it: the generator writes a file.
OSM_THROTTLE_SECONDS = 5.0

# The six reviewed files the gate reads; the generator refuses to write without them (D-10).
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
COMMENT_NAME = "changeset_comment.txt"

# Any of these in a URL means a human has not published it yet (BLOCKER 2, WARNING 7).
PLACEHOLDER_MARKERS = ("<", "TODO", "to be published")
# The template's hole for the published wiki page; the gate refuses a template without it.
WIKI_URL_PLACEHOLDER = "{wiki_url}"

# Why a selected place produced no element. Stable strings: the report prints them verbatim.
NO_ANSWER = "no answer both redistributable to osm and mapped to a reviewed tag"
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
    comment_path: Path | None = None


def format_publish_report(report: OsmPublishReport) -> list[str]:
    lines = [f"osm publish: emitted={report.emitted} elements={report.element_count}"]
    lines.extend(
        f"  not emitted ({reason}): {count}" for reason, count in sorted(report.not_emitted.items())
    )
    if report.comment_path is not None:
        lines.append(f"  changeset comment: {report.comment_path}")
    return lines


@dataclass(frozen=True)
class PublishGate:
    """The reviewed artefacts, read once; a ``pending`` flag or a placeholder lives here too."""

    import_plan: str
    wiki_page: str
    discussion_url: str
    changeset_comment_template: str
    bot_account: str
    tos_consent: str

    @property
    def wiki_url(self) -> str:
        """The ``url:`` line of the wiki page's front matter, or ``""`` when absent."""
        lines = self.wiki_page.splitlines()
        if not lines or lines[0].strip() != "---":
            return ""
        for line in lines[1:]:
            if line.strip() == "---":
                break
            key, _, value = line.partition(":")
            if key.strip() == "url":
                return value.strip()
        return ""


def _read_artefact(osm_dir: Path, name: str) -> str:
    path = osm_dir / name
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DomainError(
            f"osm publish refused: {path} is missing or unreadable ({exc}); OSM's automated-edit "
            "policy requires every artefact before a changeset may be generated (D-10)"
        ) from exc


def load_publish_gate(data_dir: Path) -> PublishGate:
    """Read the six reviewed files; a missing one is refused before any content is judged."""
    osm_dir = data_dir / "osm"
    return PublishGate(
        import_plan=_read_artefact(osm_dir, "import_plan.md"),
        wiki_page=_read_artefact(osm_dir, "wiki_page.md"),
        discussion_url=_read_artefact(osm_dir, "discussion_url.txt"),
        changeset_comment_template=_read_artefact(osm_dir, "changeset_comment_template.txt"),
        bot_account=_read_artefact(osm_dir, "bot_account.md"),
        tos_consent=_read_artefact(osm_dir, TOS_CONSENT),
    )


def _require_real_url(label: str, value: str) -> None:
    """A missing, non-``https://`` or placeholder URL refuses the run (BLOCKER 2)."""
    if not value.startswith("https://") or any(marker in value for marker in PLACEHOLDER_MARKERS):
        raise DomainError(
            f"osm publish refused: {label} must be a real https:// URL, not '{value}'; publish it "
            "before generating a changeset the community will be pointed at (D-10)"
        )


def assert_publish_gate(gate: PublishGate) -> None:
    """Refuse until every artefact is present, substantive, published, and the consent is real."""
    contents = {
        "import_plan.md": gate.import_plan,
        "wiki_page.md": gate.wiki_page,
        "discussion_url.txt": gate.discussion_url,
        "changeset_comment_template.txt": gate.changeset_comment_template,
        "bot_account.md": gate.bot_account,
        TOS_CONSENT: gate.tos_consent,
    }
    for name, content in contents.items():
        if not content.strip():
            raise DomainError(
                f"osm publish refused: {name} is empty; OSM's policy requires it (D-10)"
            )
    # Only the trailing newline is stripped: `accepted ` is not consent, and `pending` never is.
    consent = gate.tos_consent.rstrip("\r\n")
    if consent != CONSENT_ACCEPTED:
        raise DomainError(
            f"osm publish refused: {TOS_CONSENT} must read '{CONSENT_ACCEPTED}', not '{consent}'; "
            "publishing requires terms-of-service consent the user granted, never one this code "
            "infers (D-11)"
        )
    if "LetMeGetIn" not in gate.changeset_comment_template:
        raise DomainError(
            "osm publish refused: changeset_comment_template.txt must name the project LetMeGetIn, "
            "because that is what an OSM reviewer looks for (D-09)"
        )
    if WIKI_URL_PLACEHOLDER not in gate.changeset_comment_template:
        raise DomainError(
            "osm publish refused: changeset_comment_template.txt must carry a "
            f"{WIKI_URL_PLACEHOLDER} placeholder so the comment can link the wiki page (D-09)"
        )
    _require_real_url("discussion_url.txt", gate.discussion_url.strip())
    _require_real_url("the wiki page url: line", gate.wiki_url)


def _licence_matrix(data_dir: Path) -> dict[tuple[str, str], bool]:
    """The reviewed redistribution matrix, as ``can_redistribute`` reads it (D-12)."""
    try:
        slugs = {licence.slug for licence in load_licences(data_dir / "licences.csv")}
        destinations = load_licence_destinations(data_dir / "licence_destinations.csv", slugs)
    except OSError as exc:
        # Fail closed: a missing reviewed matrix must not fall through as an empty allow-set.
        raise DomainError(f"osm publish refused: the licence matrix is unreadable: {exc}") from exc
    return {(row.licence_slug, row.destination): row.allowed for row in destinations}


def _invert(mapping: AccessibilityMapping) -> dict[tuple[str, str], tuple[str, str]]:
    """``(criterion_slug, criterion_value) -> (osm_key, osm_value)``: the write-back direction."""
    return {
        (criterion_slug, criterion_value): (osm_key, osm_value)
        for (osm_key, osm_value), (criterion_slug, criterion_value) in mapping.items()
    }


def _mapped_tags(
    answers: Iterable[PlaceAccessibility],
    inverse: Mapping[tuple[str, str], tuple[str, str]],
    matrix: Mapping[tuple[str, str], bool],
) -> dict[str, str]:
    """The answers we may send to OSM (D-12) that a reviewed inverse mapping can express as tags."""
    tags: dict[str, str] = {}
    for answer in answers:
        if not can_redistribute(answer.source_license, "osm", matrix):
            continue
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
    """Write ``answers.osmChange`` and its changeset comment for every OSM place we may publish.

    Elements are ordered by numeric object id, so two runs over the same data produce the same
    document. The file is written even when nothing is emitted: an empty ``osmChange`` is a
    valid, reviewable answer, and the gate is what decides whether it may exist at all.
    """
    gate = load_publish_gate(data_dir)
    assert_publish_gate(gate)
    matrix = _licence_matrix(data_dir)
    accessibility = load_osm_accessibility_tags(data_dir / "osm_accessibility_tags.csv")
    inverse = _invert(accessibility)

    places_of_source = await places.list_by_source(SOURCE)
    answers = await places.list_accessibility_for_places([place.id for place in places_of_source])

    report = OsmPublishReport()
    elements: list[tuple[int, str]] = []
    for place in places_of_source:
        mapped = _mapped_tags(answers.get(place.id, ()), inverse, matrix)
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
    # The gate refused a placeholder wiki URL before this point, so the comment cannot carry one.
    comment = gate.changeset_comment_template.replace(WIKI_URL_PLACEHOLDER, gate.wiki_url)
    _write_atomic(out / COMMENT_NAME, comment.encode("utf-8"))
    report.element_count = len(elements)
    report.comment_path = out / COMMENT_NAME
    return report
