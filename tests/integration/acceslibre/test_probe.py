"""Integration tests: the read-only probe records the rule from a stub, never a socket."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import httpx
import pytest

from letmegetin.admin import _IDENTIFIER_RULE_FILE, probe_identifier
from letmegetin.core.exceptions import DomainError
from letmegetin.infrastructure.acceslibre.client import AccesLibreClient

_ORIGIN_ID = "12345"
_KEY = "test-key"
_SECTIONS = {"entree": {"entree_pmr": True}, "interieur": {}}


def _rule_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def _stub(
    erps: list[dict[str, Any]],
) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    """A transport returning ``erps`` from both list lookups, plus one ERP detail."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/api/erps/":
            return httpx.Response(200, json={"count": len(erps), "results": erps})
        return httpx.Response(200, json={"slug": erps[0]["slug"], "accessibilite": _SECTIONS})

    return httpx.MockTransport(handler), seen


def _probe(path: Path, erps: list[dict[str, Any]]) -> tuple[str, list[httpx.Request]]:
    transport, seen = _stub(erps)
    client = AccesLibreClient(_KEY, transport=transport)
    try:
        report = probe_identifier(client, _ORIGIN_ID, path)
    finally:
        client.close()
    return report, seen


def test_a_slug_equal_to_origin_id_records_the_origin_id_rule(tmp_path: Path) -> None:
    report, _ = _probe(tmp_path / _IDENTIFIER_RULE_FILE, [{"slug": _ORIGIN_ID}])

    assert _rule_rows(tmp_path / _IDENTIFIER_RULE_FILE)[0]["rule"] == "origin_id"
    assert "rule recorded" in report


def test_a_differing_slug_records_the_slug_rule(tmp_path: Path) -> None:
    report, _ = _probe(tmp_path / _IDENTIFIER_RULE_FILE, [{"slug": "musee-x"}])

    rows = _rule_rows(tmp_path / _IDENTIFIER_RULE_FILE)
    assert rows[0]["rule"] == "slug"
    assert "musee-x" in rows[0]["detail"]
    assert "erp_slug" in rows[0]["detail"]
    assert "rule recorded" in report


def test_no_erp_from_either_lookup_records_the_blocked_rule(tmp_path: Path) -> None:
    report, seen = _probe(tmp_path / _IDENTIFIER_RULE_FILE, [])

    assert _rule_rows(tmp_path / _IDENTIFIER_RULE_FILE)[0]["rule"] == "blocked"
    # No ERP means no detail call: A2 is not reachable for this origin_id.
    assert len(seen) == 2
    assert "accessibilite keys" not in report


def test_both_lookups_are_tried_and_get_erp_confirms_a2(tmp_path: Path) -> None:
    report, seen = _probe(tmp_path / _IDENTIFIER_RULE_FILE, [{"slug": "musee-x"}])

    urls = [str(request.url) for request in seen]
    assert any("uuid=12345" in url for url in urls)
    assert any("source=acceslibre" in url and "source_id=12345" in url for url in urls)
    assert urls[-1].endswith("/api/erps/musee-x/")
    assert "accessibilite keys (musee-x): entree, interieur" in report
    assert seen[0].headers["Authorization"] == f"Api-Key {_KEY}"


def test_a_refused_lookup_writes_no_rule(tmp_path: Path) -> None:
    path = tmp_path / _IDENTIFIER_RULE_FILE
    path.write_text("rule;detail\nblocked;UNVERIFIED\n", encoding="utf-8")
    transport = httpx.MockTransport(lambda request: httpx.Response(403))

    client = AccesLibreClient(_KEY, transport=transport)
    try:
        with pytest.raises(DomainError, match="403"):
            probe_identifier(client, _ORIGIN_ID, path)
    finally:
        client.close()

    assert "UNVERIFIED" in path.read_text(encoding="utf-8")
