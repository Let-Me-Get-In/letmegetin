"""Use case: create an account (AUTH-01)."""

from __future__ import annotations

import re

from letmegetin.core.exceptions import DomainError, EmailAlreadyUsed
from letmegetin.core.security import hash_password
from letmegetin.domain.accounts.entities import User
from letmegetin.domain.accounts.repositories import UserRepository

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


async def register(
    users: UserRepository,
    email: str,
    password: str,
    display_name: str | None = None,
) -> User:
    """Register a new account, or raise on invalid input or a duplicate email."""
    normalized = email.strip().lower()
    if not _EMAIL.match(normalized):
        raise DomainError("invalid email address")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise DomainError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
    if await users.get_by_email(normalized) is not None:
        raise EmailAlreadyUsed(normalized)
    return await users.add(
        User(
            id=0,
            email=normalized,
            password_hash=hash_password(password),
            display_name=display_name.strip() if display_name and display_name.strip() else None,
        )
    )
