"""AccesLibre outbound HTTP adapter: fixed origin, Api-Key auth, bounded retry (D-13).

The only module that imports httpx. The origin is a module constant and never a setting:
a configurable host would let a misconfiguration forward the partner key to a third party
(T-15-03). For the same reason redirects are not followed (T-15-04).
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from letmegetin.core.exceptions import DomainError

ACCESLIBRE_ORIGIN = "https://acceslibre.beta.gouv.fr"

_TIMEOUT_SECONDS = 30.0

# No published quota exists (A5): serial requests, a fixed small pause, a bounded count.
MAX_ATTEMPTS = 3
RETRY_PAUSE_SECONDS = 1.0
_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


def _retry_pause(response: httpx.Response) -> float:
    """Honour ``Retry-After`` when the server sends seconds, else pause the fixed amount."""
    header = response.headers.get("Retry-After")
    if header is None:
        return RETRY_PAUSE_SECONDS
    try:
        return max(float(header), 0.0)
    except ValueError:
        return RETRY_PAUSE_SECONDS


class AccesLibreClient:
    """The infrastructure half of ``AccesLibrePort`` (domain/places/acceslibre_push.py)."""

    def __init__(self, key: str | None, transport: httpx.BaseTransport | None = None) -> None:
        headers = {"Authorization": f"Api-Key {key}"} if key is not None else {}
        self._http = httpx.Client(
            base_url=ACCESLIBRE_ORIGIN,
            timeout=_TIMEOUT_SECONDS,
            verify=True,
            follow_redirects=False,
            headers=headers,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def get_erp(self, slug: str) -> dict[str, Any]:
        response = self._request("GET", f"api/erps/{slug}/", slug)
        return self._json(response)

    def patch_erp(self, slug: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request("PATCH", f"api/erps/{slug}/", slug, json=payload)
        return self._json(response)

    def list_erps(self, **filters: Any) -> list[dict[str, Any]]:
        response = self._request("GET", "api/erps/", "", params=filters)
        body = self._json(response)
        # A list endpoint is paginated upstream: unwrap the page, keep a bare list as is.
        if isinstance(body, dict) and isinstance(body.get("results"), list):
            return body["results"]
        return body

    @staticmethod
    def _error(status: int, slug: str) -> DomainError:
        """An error whose text carries the slug and the status, never the key or a header."""
        return DomainError(f"acceslibre refused '{slug}' with HTTP {status}")

    def _send(self, method: str, path: str, slug: str, **kwargs: Any) -> httpx.Response:
        try:
            return self._http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            # The exception's own text can carry a URL; only its class is safe to repeat.
            raise DomainError(
                f"acceslibre {method} '{slug}' unreachable: {type(exc).__name__}"
            ) from exc

    def _request(self, method: str, path: str, slug: str, **kwargs: Any) -> httpx.Response:
        response = self._send_with_retry(method, path, slug, **kwargs)
        if response.status_code >= 400:
            raise self._error(response.status_code, slug)
        return response

    def _send_with_retry(self, method: str, path: str, slug: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            response = self._send(method, path, slug, **kwargs)
            if response.status_code not in _RETRY_STATUSES or attempt == MAX_ATTEMPTS:
                return response
            time.sleep(_retry_pause(response))
        raise AssertionError("unreachable: MAX_ATTEMPTS is at least 1")

    @staticmethod
    def _json(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            raise DomainError(
                f"acceslibre returned a non-JSON body with HTTP {response.status_code}"
            ) from exc
