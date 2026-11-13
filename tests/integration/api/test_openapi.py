"""The published OpenAPI schema must keep the public contract."""

from __future__ import annotations

from letmegetin.domain.places.documentation import DOCUMENTATION_LADDER
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


def test_openapi_documents_the_documentation_contract() -> None:
    """D-09: the flag, the six slugs with their bounds, and the family shape are public."""
    schema = app.openapi()
    properties = schema["components"]["schemas"]["PlaceDetailOut"]["properties"]

    # Loop the ladder rather than a subset: a wrong bound on any level fails here.
    for slug, low, high in DOCUMENTATION_LADDER:
        bounds = f"{slug} ({low},{high})"
        assert bounds in properties["documentation_ladder"]["description"], bounds
        assert bounds in properties["accessibility_by_family"]["description"], bounds

    for field in ("documentation_ladder", "accessibility_by_family"):
        assert "stable enum, not display text" in properties[field]["description"], field

    assert "{rate, percent, level}" in properties["accessibility_by_family"]["description"]
    assert "single server source" in properties["documentation_ladder"]["description"]

    rung = schema["components"]["schemas"]["DocumentationLevelOut"]["properties"]
    assert set(rung) == {"slug", "min", "max"}

    parameters = schema["paths"]["/api/v1/places"]["get"]["parameters"]
    flag = [parameter for parameter in parameters if parameter["name"] == "with_documentation"]
    assert len(flag) == 1
    assert flag[0]["in"] == "query"
    assert "documentation" in flag[0]["description"]
