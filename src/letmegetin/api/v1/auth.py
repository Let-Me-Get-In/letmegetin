"""Auth API: register, login, refresh and the current account (AUTH-01/02)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from letmegetin.api.deps import CurrentUser, DbSession, UserRepo
from letmegetin.api.schemas.auth import (
    LoginIn,
    RefreshIn,
    RegisterIn,
    TokenPairOut,
    UserOut,
)
from letmegetin.application.accounts.login import authenticate
from letmegetin.application.accounts.register import register
from letmegetin.config import settings
from letmegetin.core.exceptions import (
    DomainError,
    EmailAlreadyUsed,
    InvalidCredentials,
    InvalidToken,
)
from letmegetin.core.security import create_token, decode_token
from letmegetin.domain.accounts.entities import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _tokens(user: User) -> TokenPairOut:
    return TokenPairOut(
        access_token=create_token(user.id, user.role, "access", settings.access_token_ttl),
        refresh_token=create_token(user.id, user.role, "refresh", settings.refresh_token_ttl),
    )


@router.post("/register", response_model=UserOut, status_code=201)
async def register_account(payload: RegisterIn, users: UserRepo, session: DbSession) -> UserOut:
    """Create an account with an email and a password."""
    try:
        user = await register(users, payload.email, payload.password, payload.display_name)
    except EmailAlreadyUsed as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except DomainError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    await session.commit()
    return UserOut.from_user(user)


@router.post("/login", response_model=TokenPairOut)
async def login(payload: LoginIn, users: UserRepo) -> TokenPairOut:
    """Return an access/refresh pair for valid credentials."""
    try:
        user = await authenticate(users, payload.email, payload.password)
    except InvalidCredentials:
        raise HTTPException(status_code=401, detail="Invalid email or password") from None
    return _tokens(user)


@router.post("/refresh", response_model=TokenPairOut)
async def refresh(payload: RefreshIn, users: UserRepo) -> TokenPairOut:
    """Exchange a valid refresh token for a fresh pair."""
    try:
        claims = decode_token(payload.refresh_token, "refresh")
    except InvalidToken:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from None
    user = await users.get_by_id(claims.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return _tokens(user)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    """Return the account behind the access token."""
    return UserOut.from_user(user)
