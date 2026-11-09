"""Retention against the real Postgres (idempotency keys and refresh tokens)."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from sqlalchemy import text
from typer.testing import CliRunner

from letmegetin import admin
from tests.db import SessionLocal, execute, require_database

_EMAIL = "test-retention@example.test"


async def _seed() -> None:
    async with SessionLocal() as session:
        user_id = await session.scalar(
            text("INSERT INTO users (email, password_hash) VALUES (:email, 'x') RETURNING id"),
            {"email": _EMAIL},
        )
        await session.execute(
            text(
                "INSERT INTO idempotency_key "
                "(user_id, key, request_hash, status_code, body, created) "
                "VALUES (:old_user, 'old', 'h', 200, '{}'::jsonb, now() - interval '2 days'), "
                "(:new_user, 'new', 'h', 200, '{}'::jsonb, now())"
            ),
            {"old_user": user_id, "new_user": user_id},
        )
        await session.execute(
            text(
                "INSERT INTO refresh_token "
                "(user_id, token_hash, expires_at, revoked, created) "
                "VALUES (:old_user, 'old-hash', now() - interval '40 days', false, "
                "now() - interval '40 days'), "
                "(:new_user, 'new-hash', now() + interval '30 days', false, now())"
            ),
            {"old_user": user_id, "new_user": user_id},
        )
        await session.commit()


async def _counts() -> tuple[int, int]:
    async with SessionLocal() as session:
        idempotency = await session.scalar(
            text(
                "SELECT count(*) FROM idempotency_key k JOIN users u ON u.id = k.user_id "
                "WHERE u.email = :email"
            ),
            {"email": _EMAIL},
        )
        refresh = await session.scalar(
            text(
                "SELECT count(*) FROM refresh_token t JOIN users u ON u.id = t.user_id "
                "WHERE u.email = :email"
            ),
            {"email": _EMAIL},
        )
    return int(idempotency or 0), int(refresh or 0)


@pytest.fixture
def db(test_sessions: None) -> Iterator[None]:
    require_database("idempotency_key")
    execute("DELETE FROM users WHERE email = :email", {"email": _EMAIL})
    asyncio.run(_seed())
    yield
    execute("DELETE FROM users WHERE email = :email", {"email": _EMAIL})


def _run(*args: str) -> str:
    result = CliRunner().invoke(admin.app, list(args))
    assert result.exit_code == 0, result.output
    return result.output


def test_retention_dry_run_keeps_rows(db: None) -> None:
    output = _run("retention", "--dry-run")

    assert "idempotency=1" in output
    assert "refresh=1" in output
    assert asyncio.run(_counts()) == (2, 2)


def test_retention_deletes_only_expired_rows(db: None) -> None:
    _run("retention")

    assert asyncio.run(_counts()) == (1, 1)
    assert _run("retention", "--dry-run").strip().endswith("idempotency=0 refresh=0 dry_run=True")
