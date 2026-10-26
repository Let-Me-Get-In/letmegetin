"""Test de la sonde de santé (sans base de données)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from jaccede.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
