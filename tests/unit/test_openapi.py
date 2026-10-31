"""The published OpenAPI schema must keep the public contract."""

from __future__ import annotations

from letmegetin.main import app


def test_openapi_exposes_the_public_contract() -> None:
    schema = app.openapi()

    assert "/api/v1/places" in schema["paths"]
    assert "/api/v1/places/{slug}" in schema["paths"]
    assert "/api/v1/places/{slug}/reviews" in schema["paths"]
    assert "/api/v1/categories/{slug}/grid" in schema["paths"]

    schemes = schema["components"]["securitySchemes"]
    assert schemes["APIKeyHeader"]["type"] == "apiKey"
    assert schemes["APIKeyHeader"]["in"] == "header"
    assert schemes["APIKeyHeader"]["name"] == "X-API-Key"
