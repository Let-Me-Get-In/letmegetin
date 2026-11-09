"""API-key CLI, authentication and rate limiting against the real Postgres."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.config import settings
from letmegetin.core.db import get_session
from letmegetin.core.security import token_fingerprint
from letmegetin.main import app

_engine = create_async_engine(settings.database_url, poolclass=NullPool)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


async def _database_ready() -> bool:
    try:
        async with _Session() as session:
            await session.execute(text("SELECT 1"))
            return await session.scalar(text("SELECT to_regclass('api_key')")) is not None
    except Exception:  # noqa: BLE001 - any connection failure means "skip"
        return False


async def _cleanup() -> None:
    async with _Session() as session:
        await session.execute(text("DELETE FROM api_key WHERE label LIKE 'test-%'"))
        await session.commit()


async def _override() -> AsyncIterator[AsyncSession]:
    async with _Session() as session:
        yield session


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    if not asyncio.run(_database_ready()):
        pytest.skip("database or api_key table unavailable")
    asyncio.run(_cleanup())
    monkeypatch.setattr(admin, "SessionLocal", _Session)
    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()
    asyncio.run(_cleanup())


def _run(*args: str) -> str:
    result = CliRunner().invoke(admin.app, list(args))
    assert result.exit_code == 0, result.output
    return result.output


def _scalar(statement: str, params: dict[str, Any] | None = None) -> Any:
    async def run() -> Any:
        async with _Session() as session:
            value = await session.scalar(text(statement), params or {})
            await session.commit()
            return value

    return asyncio.run(run())


def _row(statement: str, params: dict[str, Any] | None = None) -> Any:
    async def run() -> Any:
        async with _Session() as session:
            row = (await session.execute(text(statement), params or {})).one()
            await session.commit()
            return row

    return asyncio.run(run())


def _create_key(rpm: int = 60) -> tuple[int, str]:
    output = _run("api-key", "create", "--label", "test-pilot", "--rpm", str(rpm))
    raw = next(line.strip() for line in output.splitlines() if line.strip().startswith("lmg_"))
    key_id = int(output.split("#")[1].split(" ")[0])
    return key_id, raw


def test_create_lists_the_hash_and_revoke_disables(client: TestClient) -> None:
    key_id, raw = _create_key(120)

    stored = _row("SELECT key_hash, rpm, active FROM api_key WHERE id = :id", {"id": key_id})
    assert stored[0] == token_fingerprint(raw)
    assert stored[1] == 120
    assert stored[2] is True

    listing = _run("api-key", "list")
    assert "test-pilot" in listing
    assert raw not in listing

    _run("api-key", "revoke", str(key_id))
    assert _scalar("SELECT active FROM api_key WHERE id = :id", {"id": key_id}) is False


def test_key_quota_and_invalid_key(client: TestClient) -> None:
    _, raw = _create_key(1)
    headers = {"X-API-Key": raw}

    first = client.get("/api/v1/categories", headers=headers)
    assert first.status_code == 200
    assert first.headers["x-ratelimit-limit"] == "1"
    assert first.headers["x-ratelimit-remaining"] == "0"

    second = client.get("/api/v1/categories", headers=headers)
    assert second.status_code == 429
    assert int(second.headers["retry-after"]) >= 1

    invalid = client.get("/api/v1/categories", headers={"X-API-Key": "lmg_nope"})
    assert invalid.status_code == 401


def test_anonymous_limit_uses_the_forwarded_client_ip(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from letmegetin.config import settings

    monkeypatch.setattr(settings, "rate_limit_default_rpm", 1)

    first = client.get("/api/v1/categories", headers={"X-Forwarded-For": "203.0.113.1"})
    blocked = client.get("/api/v1/categories", headers={"X-Forwarded-For": "203.0.113.1"})
    other = client.get("/api/v1/categories", headers={"X-Forwarded-For": "203.0.113.2"})

    assert first.status_code == 200
    assert blocked.status_code == 429
    assert other.status_code == 200


def test_public_traffic_does_not_spend_the_auth_budget(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from letmegetin.config import settings

    monkeypatch.setattr(settings, "rate_limit_auth_rpm", 1)
    monkeypatch.setattr(settings, "rate_limit_default_rpm", 50)

    browsing = [client.get("/api/v1/categories") for _ in range(3)]
    login = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.org", "password": "wrong-one"}
    )

    assert [response.status_code for response in browsing] == [200, 200, 200]
    assert login.status_code != 429


def test_me_does_not_spend_the_auth_budget(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from letmegetin.config import settings

    monkeypatch.setattr(settings, "rate_limit_auth_rpm", 1)
    monkeypatch.setattr(settings, "rate_limit_default_rpm", 50)
    headers = {"X-Forwarded-For": "203.0.113.48"}

    # `me` runs on every page load: only the 401 may come back, never a 429.
    me = [client.get("/api/v1/auth/me", headers=headers) for _ in range(3)]
    assert [response.status_code for response in me] == [401, 401, 401]

    # The credential endpoint keeps the tight window.
    credentials = {"email": "nobody@example.org", "password": "wrong-one"}
    login = {"X-Forwarded-For": "203.0.113.49"}
    first = client.post("/api/v1/auth/login", json=credentials, headers=login)
    second = client.post("/api/v1/auth/login", json=credentials, headers=login)

    assert first.status_code == 401
    assert second.status_code == 429


def test_error_responses_carry_the_rate_limit_headers(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from letmegetin.config import settings

    monkeypatch.setattr(settings, "rate_limit_default_rpm", 50)
    monkeypatch.setattr(settings, "rate_limit_auth_rpm", 10)
    headers = {"X-Forwarded-For": "203.0.113.61"}

    ok = client.get("/api/v1/categories", headers=headers)
    unauthorised = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.org", "password": "wrong-one"},
        headers={"X-Forwarded-For": "203.0.113.62"},
    )

    assert ok.headers["x-ratelimit-remaining"] == "49"
    assert unauthorised.status_code == 401
    assert unauthorised.headers["x-ratelimit-limit"] == "10"
    assert unauthorised.headers["x-ratelimit-remaining"] == "9"
