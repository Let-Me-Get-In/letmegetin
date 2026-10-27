"""Use case: authenticate an email/password pair (AUTH-02)."""

from __future__ import annotations

from letmegetin.core.exceptions import InvalidCredentials
from letmegetin.core.security import verify_password
from letmegetin.domain.accounts.entities import User
from letmegetin.domain.accounts.repositories import UserRepository


async def authenticate(users: UserRepository, email: str, password: str) -> User:
    """Return the account, or raise ``InvalidCredentials`` without revealing which part failed."""
    user = await users.get_by_email(email.strip().lower())
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentials()
    return user
