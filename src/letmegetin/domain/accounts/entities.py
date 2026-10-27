"""Accounts context: users and their roles."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["User"]


@dataclass
class User:
    """An account: credentials, role and public display name."""

    id: int
    email: str
    password_hash: str
    role: str = "user"
    display_name: str | None = None
