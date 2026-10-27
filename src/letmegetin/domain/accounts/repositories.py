"""Accounts context: the user repository port."""

from __future__ import annotations

from typing import Protocol

from letmegetin.domain.accounts.entities import User


class UserRepository(Protocol):
    """Read/write access to accounts."""

    async def get_by_email(self, email: str) -> User | None: ...

    async def get_by_id(self, user_id: int) -> User | None: ...

    async def add(self, user: User) -> User: ...
