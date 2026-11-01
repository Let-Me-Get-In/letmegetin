"""Prometheus payload and request recording."""

from __future__ import annotations

from letmegetin.core.metrics import record_request, render_metrics


def test_metrics_payload_contains_the_request_counter() -> None:
    record_request("GET", "/api/v1/places", 200, 0.012)

    payload, content_type = render_metrics()

    assert b"letmegetin_http_requests_total" in payload
    assert b'path="/api/v1/places"' in payload
    assert "text/plain" in content_type
