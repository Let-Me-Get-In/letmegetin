"""Unit tests for the account use cases (register, authenticate)."""

from __future__ import annotations

import pytest

from letmegetin.application.accounts.login import authenticate
from letmegetin.application.accounts.register import register
from letmegetin.core.exceptions import DomainError, EmailAlreadyUsed, InvalidCredentials
from letmegetin.domain.accounts.entities import User


class _Users:
    def __init__(self, users: list[User] | None = None) -> None:
        self._users = {user.email: user for user in users or []}
        self._next_id = max((user.id for user in self._users.values()), default=0) + 1

    async def get_by_email(self, email: str) -> User | None:
        return self._users.get(email)

    async def get_by_id(self, user_id: int) -> User | None:
        return next((user for user in self._users.values() if user.id == user_id), None)

    async def add(self, user: User) -> User:
        stored = User(
            id=self._next_id,
            email=user.email,
            password_hash=user.password_hash,
            role=user.role,
            display_name=user.display_name,
        )
        self._users[stored.email] = stored
        self._next_id += 1
        return stored


async def test_register_normalizes_the_email_and_display_name() -> None:
    user = await register(_Users(), "  Alice@Example.TEST ", "password123", "  Alice ")

    assert (user.email, user.display_name, user.role) == ("alice@example.test", "Alice", "user")


@pytest.mark.parametrize("email", ["nope", "a@b", "@example.test", "a b@example.test"])
async def test_register_rejects_invalid_emails(email: str) -> None:
    with pytest.raises(DomainError):
        await register(_Users(), email, "password123")


async def test_register_rejects_a_short_password() -> None:
    with pytest.raises(DomainError):
        await register(_Users(), "alice@example.test", "short")


async def test_register_rejects_a_duplicate_email() -> None:
    users = _Users()
    await register(users, "alice@example.test", "password123")

    with pytest.raises(EmailAlreadyUsed):
        await register(users, "ALICE@example.test", "password123")


async def test_authenticate_returns_the_account() -> None:
    users = _Users()
    await register(users, "alice@example.test", "password123")

    user = await authenticate(users, "ALICE@example.test", "password123")

    assert user.email == "alice@example.test"


@pytest.mark.parametrize(
    "email,password", [("alice@example.test", "wrong"), ("no@example.test", "password123")]
)
async def test_authenticate_rejects_bad_credentials(email: str, password: str) -> None:
    users = _Users()
    await register(users, "alice@example.test", "password123")

    with pytest.raises(InvalidCredentials):
        await authenticate(users, email, password)
