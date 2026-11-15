"""Unit checks: fixed origin, TLS on, no redirects, key never in an error (T-15-03/04)."""

from __future__ import annotations

from typing import Any

import httpx

from letmegetin.config import Settings
from letmegetin.infrastructure.acceslibre.client import ACCESLIBRE_ORIGIN, AccesLibreClient

_KEY = "s3cr3t-partner-key"


def test_origin_is_the_acceslibre_host() -> None:
    assert ACCESLIBRE_ORIGIN == "https://acceslibre.beta.gouv.fr"


def test_client_uses_the_constant_origin_verifies_tls_and_does_not_follow_redirects(
    monkeypatch,
) -> None:
    built: dict[str, object] = {}
    real_client = httpx.Client

    def spy(*args: Any, **kwargs: Any) -> httpx.Client:
        built.update(kwargs)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", spy)
    client = AccesLibreClient(_KEY)

    assert built["base_url"] == ACCESLIBRE_ORIGIN
    assert built["verify"] is True
    assert built["follow_redirects"] is False
    assert str(client._http.base_url) == ACCESLIBRE_ORIGIN
    assert client._http.follow_redirects is False
    client.close()


def test_error_text_carries_the_slug_and_the_status_but_never_the_key() -> None:
    message = str(AccesLibreClient._error(401, "musee-x"))

    assert "401" in message
    assert "musee-x" in message
    assert _KEY not in message


def test_the_only_acceslibre_setting_is_the_key() -> None:
    """A host setting would be a key-exfiltration path: it must never come back."""
    assert [name for name in Settings.model_fields if name.startswith("acceslibre_")] == [
        "acceslibre_api_key"
    ]
