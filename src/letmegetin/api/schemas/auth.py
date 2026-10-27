"""Pydantic request/response schemas for the auth API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from letmegetin.domain.accounts.entities import User


class RegisterIn(BaseModel):
    """Sign-up payload."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)


class LoginIn(BaseModel):
    """Login payload."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(BaseModel):
    """Refresh payload."""

    refresh_token: str


class TokenPairOut(BaseModel):
    """An access/refresh pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    """The public account shape (never the hash, never the token)."""

    id: int
    email: str
    role: str
    display_name: str | None = None

    @classmethod
    def from_user(cls, user: User) -> UserOut:
        return cls(
            id=user.id,
            email=user.email,
            role=user.role,
            display_name=user.display_name,
        )
