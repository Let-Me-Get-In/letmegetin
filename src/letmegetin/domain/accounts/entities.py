"""Accounts context: users and their roles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

__all__ = ["ApiKey", "RefreshToken", "User"]


@dataclass
class User:
    """An account: credentials, role and public display name."""

    id: int
    email: str
    password_hash: str
    role: str = "user"
    display_name: str | None = None
    email_verified: bool = False


@dataclass
class RefreshToken:
    """A server-side refresh-token record (only its fingerprint is stored)."""

    user_id: int
    expires_at: datetime
    revoked: bool = False


@dataclass
class ApiKey:
    """A partner API key; only the SHA-256 hash is persisted."""

    id: int
    label: str
    key_hash: str
    rpm: int = 60
    active: bool = True
