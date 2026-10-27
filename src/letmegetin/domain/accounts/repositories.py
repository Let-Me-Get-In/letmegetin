"""Accounts context: the user repository port."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from letmegetin.domain.accounts.entities import RefreshToken, User


class UserRepository(Protocol):
    """Read/write access to accounts."""

    async def get_by_email(self, email: str) -> User | None: ...

    async def get_by_id(self, user_id: int) -> User | None: ...

    async def add(self, user: User) -> User: ...

    async def mark_email_verified(self, user_id: int) -> User | None: ...


class RefreshTokenRepository(Protocol):
    """Server-side refresh-token store, keyed by a hash of the token."""

    async def add(self, user_id: int, token_hash: str, expires_at: datetime) -> None: ...

    async def get(self, token_hash: str) -> RefreshToken | None: ...

    async def revoke(self, token_hash: str) -> None: ...
