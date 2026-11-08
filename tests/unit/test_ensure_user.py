"""Unit tests for the `ensure_user` seeding use case (E2E-01)."""

from __future__ import annotations

import pytest

from letmegetin.application.accounts.users import ensure_user
from letmegetin.core.exceptions import DomainError
from letmegetin.core.security import hash_password, verify_password
from letmegetin.domain.accounts.entities import User

_PASSWORD = "e2e-secret-1"


class _Users:
    """In-memory `UserRepository` over a dict keyed by email."""

    def __init__(self) -> None:
        self.rows: dict[str, User] = {}
        self._next = 1

    async def get_by_email(self, email: str) -> User | None:
        return self.rows.get(email)

    async def get_by_id(self, user_id: int) -> User | None:
        return next((row for row in self.rows.values() if row.id == user_id), None)

    async def add(self, user: User) -> User:
        stored = User(
            id=self._next,
            email=user.email,
            password_hash=user.password_hash,
            role=user.role,
            display_name=user.display_name,
            email_verified=user.email_verified,
        )
        self.rows[stored.email] = stored
        self._next += 1
        return stored

    async def mark_email_verified(self, user_id: int) -> User | None:
        row = await self.get_by_id(user_id)
        if row is not None:
            row.email_verified = True
        return row


def _seeded(*, verified: bool) -> _Users:
    users = _Users()
    users.rows["e2e@example.test"] = User(
        id=1,
        email="e2e@example.test",
        password_hash="",
        email_verified=verified,
    )
    users._next = 2
    return users


@pytest.mark.parametrize("verified", [True, False])
async def test_ensure_user_fresh_email_creates_one_verified_row(verified: bool) -> None:
    users = _Users()

    outcome = await ensure_user(users, "  E2E@Example.test ", _PASSWORD, " E2E ", verified)

    assert outcome == "created"
    stored = users.rows["e2e@example.test"]
    assert stored.email_verified is verified
    assert stored.display_name == "E2E"
    assert verify_password(_PASSWORD, stored.password_hash)
    assert not verify_password("wrong-password", stored.password_hash)


async def test_ensure_user_verifies_an_existing_unverified_account_once() -> None:
    users = _seeded(verified=False)
    users.rows["e2e@example.test"].password_hash = hash_password(_PASSWORD)

    outcome = await ensure_user(users, "e2e@example.test", _PASSWORD, verified=True)

    assert outcome == "verified"
    assert users.rows["e2e@example.test"].email_verified is True
    assert len(users.rows) == 1


async def test_ensure_user_reports_an_already_verified_account() -> None:
    users = _seeded(verified=True)
    users.rows["e2e@example.test"].password_hash = hash_password(_PASSWORD)

    assert await ensure_user(users, "e2e@example.test", _PASSWORD, verified=True) == (
        "already verified"
    )


async def test_ensure_user_reports_an_unverified_account_left_alone() -> None:
    users = _seeded(verified=False)
    users.rows["e2e@example.test"].password_hash = hash_password(_PASSWORD)

    assert await ensure_user(users, "e2e@example.test", _PASSWORD) == "unverified"
    assert users.rows["e2e@example.test"].email_verified is False


async def test_ensure_user_fails_on_a_password_mismatch() -> None:
    users = _seeded(verified=True)
    users.rows["e2e@example.test"].password_hash = hash_password(_PASSWORD)

    with pytest.raises(DomainError) as raised:
        await ensure_user(users, "e2e@example.test", "different-secret", verified=True)

    assert _PASSWORD not in str(raised.value)
    assert "different-secret" not in str(raised.value)


@pytest.mark.parametrize("email", ["", "not-an-email", "no@domain"])
async def test_ensure_user_rejects_an_invalid_email(email: str) -> None:
    with pytest.raises(DomainError):
        await ensure_user(_Users(), email, _PASSWORD, verified=True)


async def test_ensure_user_rejects_a_short_password() -> None:
    with pytest.raises(DomainError):
        await ensure_user(_Users(), "e2e@example.test", "short", verified=True)


async def test_ensure_user_never_returns_the_password() -> None:
    outcome = await ensure_user(_Users(), "e2e@example.test", _PASSWORD, verified=True)

    assert _PASSWORD not in outcome
