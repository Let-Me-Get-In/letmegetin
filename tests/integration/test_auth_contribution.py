"""Auth, contribution and review-write integration tests against the real database.

Skips cleanly when the container or migration 0005 is absent.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from letmegetin.config import settings
from letmegetin.core.db import get_session
from letmegetin.core.security import create_token
from letmegetin.domain.places.dedup import normalize_name
from letmegetin.main import app

_engine = create_async_engine(settings.database_url, poolclass=NullPool)
_TestSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

_SLUG = "test-p5-place-00000000"
_EMAIL = "test-p5-user@example.test"
_PASSWORD = "password123"
_TREE = [
    {
        "slug": "test-p5-group",
        "label": {"fr": "Groupe"},
        "type": "array",
        "children": [
            {"slug": "test-p5-a", "label": {"fr": "A"}, "type": "boolean", "children": []},
            {"slug": "test-p5-b", "label": {"fr": "B"}, "type": "boolean", "children": []},
        ],
    }
]


async def _database_ready() -> bool:
    try:
        async with _TestSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return await session.scalar(text("SELECT to_regclass('users')")) is not None
    except Exception:  # noqa: BLE001 - any connection failure means "skip"
        return False


async def _cleanup() -> None:
    async with _TestSessionLocal() as session:
        await session.execute(text("DELETE FROM place WHERE source = 'test-p5'"))
        await session.execute(text("DELETE FROM criteria WHERE slug LIKE 'test-p5-%'"))
        await session.execute(
            text(
                "DELETE FROM category_grid WHERE category_id IN "
                "(SELECT id FROM categories WHERE slug = 'test-p5-cat')"
            )
        )
        await session.execute(text("DELETE FROM categories WHERE slug = 'test-p5-cat'"))
        await session.execute(text("DELETE FROM users WHERE email LIKE 'test-p5-%'"))
        await session.commit()


async def _seed() -> None:
    async with _TestSessionLocal() as session:
        category_id = await session.scalar(
            text(
                "INSERT INTO categories (slug, name, label) "
                "VALUES ('test-p5-cat', 'Test', '{}') RETURNING id"
            )
        )
        await session.execute(
            text(
                "INSERT INTO category_grid (category_id, version, tree) "
                "VALUES (:category_id, 1, CAST(:tree AS jsonb))"
            ),
            {"category_id": category_id, "tree": json.dumps(_TREE)},
        )
        await session.execute(
            text(
                "INSERT INTO place (source, source_id, name, name_normalized, slug, "
                "category_id, lat, lng) VALUES ('test-p5', 'test-p5-1', 'Test Phase Cinq', "
                ":normalized, :slug, :category_id, 45.0, 5.0)"
            ),
            {
                "normalized": normalize_name("Test Phase Cinq"),
                "slug": _SLUG,
                "category_id": category_id,
            },
        )
        await session.execute(
            text(
                "INSERT INTO criteria (slug, parent_id, type, position, need_children, label, "
                "description) VALUES ('test-p5-a', NULL, 'boolean', 0, false, '{}', '{}'), "
                "('test-p5-b', NULL, 'boolean', 1, false, '{}', '{}')"
            )
        )
        await session.commit()


async def _override() -> AsyncIterator[AsyncSession]:
    async with _TestSessionLocal() as session:
        yield session


@pytest.fixture
def client() -> Iterator[TestClient]:
    if not asyncio.run(_database_ready()):
        pytest.skip("database or users table unavailable")
    asyncio.run(_cleanup())
    asyncio.run(_seed())
    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()
    asyncio.run(_cleanup())


def _register(client: TestClient, email: str = _EMAIL) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": _PASSWORD, "display_name": "Alice"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _tokens(client: TestClient, email: str = _EMAIL) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": _PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()


def _auth(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _verify(client: TestClient, user: dict[str, Any]) -> None:
    token = create_token(user["id"], user["role"], "verify", 60)
    response = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert response.status_code == 200, response.text


def _scalar(statement: str, params: dict[str, Any] | None = None) -> Any:
    async def run() -> Any:
        async with _TestSessionLocal() as session:
            value = await session.scalar(text(statement), params or {})
            await session.commit()
            return value

    return asyncio.run(run())


def _execute(statement: str, params: dict[str, Any] | None = None) -> None:
    async def run() -> None:
        async with _TestSessionLocal() as session:
            await session.execute(text(statement), params or {})
            await session.commit()

    asyncio.run(run())


def test_register_login_me_and_refresh(client: TestClient) -> None:
    user = _register(client)
    assert (user["email"], user["role"], "password_hash" in user) == (_EMAIL, "user", False)
    assert user["email_verified"] is False

    duplicate = client.post("/api/v1/auth/register", json={"email": _EMAIL, "password": _PASSWORD})
    assert duplicate.status_code == 409

    assert (
        client.post("/api/v1/auth/login", json={"email": _EMAIL, "password": "bad"}).status_code
        == 401
    )

    tokens = _tokens(client)
    me = client.get("/api/v1/auth/me", headers=_auth(tokens))
    assert (me.status_code, me.json()["email"]) == (200, _EMAIL)

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["token_type"] == "bearer"

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401

    new_refresh = refreshed.json()["refresh_token"]
    assert (
        client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh}).status_code == 204
    )
    assert (
        client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh}).status_code == 401
    )

    as_access = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert as_access.status_code == 401


def test_contribution_updates_the_value_logs_it_and_recomputes_the_rate(
    client: TestClient,
) -> None:
    user = _register(client)
    tokens = _tokens(client)

    anonymous = client.put(f"/api/v1/places/{_SLUG}/accessibility/test-p5-a", json={"value": True})
    assert anonymous.status_code == 401

    unverified = client.put(
        f"/api/v1/places/{_SLUG}/accessibility/test-p5-a",
        json={"value": True},
        headers=_auth(tokens),
    )
    assert unverified.status_code == 403
    _verify(client, user)

    response = client.put(
        f"/api/v1/places/{_SLUG}/accessibility/test-p5-a",
        json={"value": True},
        headers=_auth(tokens),
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"criterion": "test-p5-a", "value": True, "filled_rate": 0.5}

    second = client.put(
        f"/api/v1/places/{_SLUG}/accessibility/test-p5-a",
        json={"value": False},
        headers=_auth(tokens),
    )
    assert second.status_code == 200
    assert second.json()["filled_rate"] == 0.5

    log = _scalar(
        "SELECT count(*) FROM contribution WHERE place_id = "
        "(SELECT id FROM place WHERE source = 'test-p5')"
    )
    stored = _scalar(
        "SELECT pa.value->>'value' FROM place_accessibility pa "
        "JOIN criteria c ON c.id = pa.criterion_id "
        "JOIN place p ON p.id = pa.place_id "
        "WHERE p.source = 'test-p5' AND c.slug = 'test-p5-a'"
    )
    assert (log, stored) == (2, "false")

    missing = client.put(
        f"/api/v1/places/{_SLUG}/accessibility/nope",
        json={"value": True},
        headers=_auth(tokens),
    )
    assert missing.status_code == 404


def test_review_creation_and_admin_moderation(client: TestClient) -> None:
    user = _register(client)
    tokens = _tokens(client)
    _verify(client, user)

    created = client.post(
        f"/api/v1/places/{_SLUG}/reviews",
        json={"rating": 4, "body": "Très bon accueil"},
        headers=_auth(tokens),
    )
    assert created.status_code == 201, created.text
    review = created.json()
    assert (review["rating"], review["author_name"], review["status"]) == (4, "Alice", "published")

    listing = client.get(f"/api/v1/places/{_SLUG}/reviews").json()
    assert (listing["total"], listing["items"][0]["body"]) == (1, "Très bon accueil")
    assert client.get(f"/api/v1/places/{_SLUG}").json()["rating"] == 4.0

    forbidden = client.patch(
        f"/api/v1/reviews/{review['id']}", json={"status": "hidden"}, headers=_auth(tokens)
    )
    assert forbidden.status_code == 403

    _execute("UPDATE users SET role = 'admin' WHERE email = :email", {"email": _EMAIL})
    hidden = client.patch(
        f"/api/v1/reviews/{review['id']}", json={"status": "hidden"}, headers=_auth(tokens)
    )
    assert (hidden.status_code, hidden.json()["status"]) == (200, "hidden")
    assert client.get(f"/api/v1/places/{_SLUG}/reviews").json()["total"] == 0
    assert client.get(f"/api/v1/places/{_SLUG}").json()["rating"] is None


def test_anonymous_review_is_rejected(client: TestClient) -> None:
    response = client.post(f"/api/v1/places/{_SLUG}/reviews", json={"rating": 5})

    assert response.status_code == 401


def test_verification_token_and_resend(client: TestClient) -> None:
    user = _register(client)
    tokens = _tokens(client)

    wrong_kind = client.post("/api/v1/auth/verify-email", json={"token": tokens["access_token"]})
    assert wrong_kind.status_code == 401

    assert client.post("/api/v1/auth/resend-verification", headers=_auth(tokens)).status_code == 202

    _verify(client, user)
    assert client.post("/api/v1/auth/resend-verification", headers=_auth(tokens)).status_code == 409


def test_contribution_is_idempotent_with_a_key(client: TestClient) -> None:
    user = _register(client)
    tokens = _tokens(client)
    _verify(client, user)
    headers = {**_auth(tokens), "Idempotency-Key": "contrib-1"}
    payload = {"value": True}

    first = client.put(
        f"/api/v1/places/{_SLUG}/accessibility/test-p5-a", json=payload, headers=headers
    )
    second = client.put(
        f"/api/v1/places/{_SLUG}/accessibility/test-p5-a", json=payload, headers=headers
    )

    assert (first.status_code, second.status_code) == (200, 200)
    assert first.json() == second.json()
    log = _scalar(
        "SELECT count(*) FROM contribution WHERE place_id = "
        "(SELECT id FROM place WHERE source = 'test-p5')"
    )
    assert log == 1

    conflict = client.put(
        f"/api/v1/places/{_SLUG}/accessibility/test-p5-a",
        json={"value": False},
        headers=headers,
    )
    assert conflict.status_code == 409


def test_contribution_value_repeat_does_not_duplicate_the_log(client: TestClient) -> None:
    user = _register(client)
    tokens = _tokens(client)
    _verify(client, user)

    first = client.put(
        f"/api/v1/places/{_SLUG}/accessibility/test-p5-a",
        json={"value": True},
        headers=_auth(tokens),
    )
    second = client.put(
        f"/api/v1/places/{_SLUG}/accessibility/test-p5-a",
        json={"value": True},
        headers=_auth(tokens),
    )

    assert (first.status_code, second.status_code) == (200, 200)
    log = _scalar(
        "SELECT count(*) FROM contribution WHERE place_id = "
        "(SELECT id FROM place WHERE source = 'test-p5')"
    )
    assert log == 1


def test_review_is_idempotent_with_a_key(client: TestClient) -> None:
    user = _register(client)
    tokens = _tokens(client)
    _verify(client, user)
    headers = {**_auth(tokens), "Idempotency-Key": "review-1"}
    payload = {"rating": 5, "body": "Accueil parfait"}

    first = client.post(f"/api/v1/places/{_SLUG}/reviews", json=payload, headers=headers)
    second = client.post(f"/api/v1/places/{_SLUG}/reviews", json=payload, headers=headers)

    assert (first.status_code, second.status_code) == (201, 201)
    assert first.json()["id"] == second.json()["id"]
    assert client.get(f"/api/v1/places/{_SLUG}/reviews").json()["total"] == 1

    conflict = client.post(
        f"/api/v1/places/{_SLUG}/reviews",
        json={"rating": 1, "body": "Autre"},
        headers=headers,
    )
    assert conflict.status_code == 409
