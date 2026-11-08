"""`admin user ensure` against the real Postgres: the operator/E2E seeding path (E2E-01)."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from typer.testing import CliRunner, Result

from letmegetin import admin
from letmegetin.config import settings
from letmegetin.core.security import verify_password

# NullPool: every CLI invocation runs its own event loop via asyncio.run.
_engine = create_async_engine(settings.database_url, poolclass=NullPool)
_TestSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

_EMAIL = "cli-test-e2e@example.test"
_PASSWORD = "e2e-secret-1"


async def _database_ready() -> bool:
    try:
        async with _TestSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return await session.scalar(text("SELECT to_regclass('users')")) is not None
    except Exception:  # noqa: BLE001 - any connection failure means "skip"
        return False


async def _cleanup() -> None:
    async with _TestSessionLocal() as session:
        await session.execute(text("DELETE FROM users WHERE email LIKE 'cli-test-%'"))
        await session.commit()


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    if not asyncio.run(_database_ready()):
        pytest.skip("database or users table unavailable")
    monkeypatch.setattr(admin, "SessionLocal", _TestSessionLocal)
    asyncio.run(_cleanup())
    yield
    asyncio.run(_cleanup())


def _rows(email: str) -> list[tuple[bool, str]]:
    async def run() -> list[tuple[bool, str]]:
        async with _TestSessionLocal() as session:
            result = await session.execute(
                text("SELECT email_verified, password_hash FROM users WHERE email = :email"),
                {"email": email},
            )
            return [(row[0], row[1]) for row in result]

    return asyncio.run(run())


def _ensure(*args: str, password: str = _PASSWORD) -> Result:
    return CliRunner().invoke(
        admin.app,
        ["user", "ensure", *args],
        env={"LETMEGETIN_USER_PASSWORD": password},
    )


def test_ensure_creates_a_verified_account_once(db: None) -> None:
    first = _ensure("cli-test-e2e@example.test", "--verified", "--display-name", "E2E")

    assert first.exit_code == 0, first.output
    assert "created" in first.output
    assert _PASSWORD not in first.output
    rows = _rows(_EMAIL)
    assert len(rows) == 1
    verified, stored = rows[0]
    assert verified is True
    assert verify_password(_PASSWORD, stored)
    assert not verify_password("wrong-password", stored)

    second = _ensure("cli-test-e2e@example.test", "--verified")

    assert second.exit_code == 0, second.output
    assert "already verified" in second.output
    assert len(_rows(_EMAIL)) == 1


def test_ensure_fails_loudly_on_a_password_mismatch(db: None) -> None:
    assert _ensure(_EMAIL, "--verified").exit_code == 0
    before = _rows(_EMAIL)

    mismatch = _ensure(_EMAIL, "--verified", password="another-secret")

    assert mismatch.exit_code == 1
    assert "does not match" in mismatch.output
    assert _rows(_EMAIL) == before


def test_ensure_rejects_a_password_option(db: None) -> None:
    result = _ensure(_EMAIL, "--password", "x")

    assert result.exit_code != 0
    assert _rows(_EMAIL) == []
