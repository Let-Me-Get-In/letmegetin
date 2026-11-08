"""Use case: idempotently seed an operator/E2E account (E2E-01)."""

from __future__ import annotations

from letmegetin.application.accounts.register import MIN_PASSWORD_LENGTH, is_valid_email
from letmegetin.core.exceptions import DomainError
from letmegetin.core.security import hash_password, verify_password
from letmegetin.domain.accounts.entities import User
from letmegetin.domain.accounts.repositories import UserRepository


async def ensure_user(
    users: UserRepository,
    email: str,
    password: str,
    display_name: str | None = None,
    verified: bool = False,
) -> str:
    """Create the account if missing, verify it, and refuse a password mismatch.

    Returns ``created``, ``verified``, ``already verified`` or ``unverified``.
    An existing account is never overwritten: a wrong password is a loud error, so a
    re-run cannot leave the account holding a secret the operator did not supply.
    """
    normalized = email.strip().lower()
    if not is_valid_email(normalized):
        raise DomainError("invalid email address")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise DomainError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")

    existing = await users.get_by_email(normalized)
    if existing is None:
        clean_name = display_name.strip() if display_name and display_name.strip() else None
        await users.add(
            User(
                id=0,
                email=normalized,
                password_hash=hash_password(password),
                display_name=clean_name,
                email_verified=verified,
            )
        )
        return "created"

    if not verify_password(password, existing.password_hash):
        raise DomainError("password does not match the existing account")
    if existing.email_verified:
        return "already verified"
    if verified:
        await users.mark_email_verified(existing.id)
        return "verified"
    return "unverified"
