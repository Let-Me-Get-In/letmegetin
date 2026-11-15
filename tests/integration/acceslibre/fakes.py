"""The shared AccesLibre stub: one handler for every client test, no socket, no key."""

from __future__ import annotations

from typing import Any

import httpx

from letmegetin.infrastructure.acceslibre.client import AccesLibreClient

ERP: dict[str, Any] = {"slug": "musee-x", "accessibilite": {"entree_pmr": True}}


def _stub(request: httpx.Request) -> httpx.Response:
    """A deterministic ERP: the list endpoint pages, everything else returns one ERP."""
    if request.method == "GET" and request.url.path == "/api/erps/":
        return httpx.Response(200, json={"count": 1, "results": [ERP]})
    return httpx.Response(200, json=ERP)


def make_client(key: str | None = "test-key") -> AccesLibreClient:
    return AccesLibreClient(key, transport=httpx.MockTransport(_stub))
