"""Integration tests: the AccesLibre adapter against an in-process stub (no socket)."""

from __future__ import annotations

import json

import httpx
import pytest

from letmegetin.core.exceptions import DomainError
from letmegetin.infrastructure.acceslibre import client as client_module
from letmegetin.infrastructure.acceslibre.client import ACCESLIBRE_ORIGIN, AccesLibreClient
from tests.integration.acceslibre.fakes import ERP

_KEY = "test-key"


@pytest.fixture(autouse=True)
def _no_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    """The retry pause is a real sleep; the suite must not wait for it."""
    monkeypatch.setattr(client_module, "RETRY_PAUSE_SECONDS", 0.0)


def _recording(seen: list[httpx.Request], *responses: httpx.Response) -> httpx.MockTransport:
    """A transport that records each request and replays ``responses`` in order."""

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return responses[min(len(seen) - 1, len(responses) - 1)]

    return httpx.MockTransport(handler)


def test_get_erp_hits_the_fixed_origin() -> None:
    seen: list[httpx.Request] = []
    client = AccesLibreClient(_KEY, transport=_recording(seen, httpx.Response(200, json=ERP)))

    body = client.get_erp("musee-x")

    assert body == ERP
    assert seen[0].method == "GET"
    assert str(seen[0].url) == f"{ACCESLIBRE_ORIGIN}/api/erps/musee-x/"
    assert seen[0].headers["Authorization"] == f"Api-Key {_KEY}"


def test_patch_erp_sends_only_the_payload_it_is_given() -> None:
    seen: list[httpx.Request] = []
    payload = {"accessibilite": {"entree_pmr": True}}
    client = AccesLibreClient(_KEY, transport=_recording(seen, httpx.Response(200, json=ERP)))

    client.patch_erp("musee-x", payload)

    assert seen[0].method == "PATCH"
    assert str(seen[0].url) == f"{ACCESLIBRE_ORIGIN}/api/erps/musee-x/"
    assert json.loads(seen[0].content) == payload


def test_list_erps_unwraps_the_page() -> None:
    seen: list[httpx.Request] = []
    page = httpx.Response(200, json={"count": 1, "results": [ERP]})
    client = AccesLibreClient(_KEY, transport=_recording(seen, page))

    assert client.list_erps(source="acceslibre") == [ERP]
    assert str(seen[0].url) == f"{ACCESLIBRE_ORIGIN}/api/erps/?source=acceslibre"


def test_an_unkeyed_client_sends_no_authorization_header() -> None:
    seen: list[httpx.Request] = []
    client = AccesLibreClient(None, transport=_recording(seen, httpx.Response(200, json=ERP)))

    client.get_erp("musee-x")

    assert "Authorization" not in seen[0].headers


@pytest.mark.parametrize("status", [401, 403])
def test_refusal_raises_with_slug_and_status_only(status: int) -> None:
    client = AccesLibreClient(_KEY, transport=_recording([], httpx.Response(status)))

    with pytest.raises(DomainError) as raised:
        client.get_erp("musee-x")

    message = str(raised.value)
    assert str(status) in message
    assert "musee-x" in message
    assert _KEY not in message


def test_rate_limit_is_retried_then_the_bound_halts() -> None:
    seen: list[httpx.Request] = []
    client = AccesLibreClient(_KEY, transport=_recording(seen, httpx.Response(429)))

    with pytest.raises(DomainError) as raised:
        client.get_erp("musee-x")

    assert len(seen) == client_module.MAX_ATTEMPTS
    assert "429" in str(raised.value)


def test_rate_limit_then_success_returns_the_body() -> None:
    seen: list[httpx.Request] = []
    client = AccesLibreClient(
        _KEY,
        transport=_recording(seen, httpx.Response(429), httpx.Response(200, json=ERP)),
    )

    assert client.get_erp("musee-x") == ERP
    assert len(seen) == 2


def test_retry_after_seconds_drives_the_pause() -> None:
    assert client_module._retry_pause(httpx.Response(429, headers={"Retry-After": "7"})) == 7.0


def test_retry_pause_falls_back_when_the_header_is_absent_or_unreadable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(client_module, "RETRY_PAUSE_SECONDS", 2.5)
    dated = httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"})

    assert client_module._retry_pause(httpx.Response(429)) == 2.5
    assert client_module._retry_pause(dated) == 2.5


def test_transport_failure_is_a_domain_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    client = AccesLibreClient(_KEY, transport=httpx.MockTransport(handler))

    with pytest.raises(DomainError) as raised:
        client.get_erp("musee-x")

    assert "ConnectError" in str(raised.value)
    assert _KEY not in str(raised.value)


def test_non_json_body_is_a_domain_error() -> None:
    client = AccesLibreClient(_KEY, transport=_recording([], httpx.Response(200, text="<html>")))

    with pytest.raises(DomainError):
        client.get_erp("musee-x")
