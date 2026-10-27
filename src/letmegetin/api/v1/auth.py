"""Auth API: register, login, refresh, logout, email verification (AUTH-01/02)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException

from letmegetin.api.deps import CurrentUser, DbSession, RefreshRepo, UserRepo
from letmegetin.api.schemas.auth import (
    LoginIn,
    LogoutIn,
    RefreshIn,
    RegisterIn,
    StatusOut,
    TokenPairOut,
    UserOut,
    VerifyEmailIn,
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
from letmegetin.core.mailer import send_verification_email
from letmegetin.core.security import create_token, decode_token, token_fingerprint
from letmegetin.domain.accounts.entities import User
from letmegetin.domain.accounts.repositories import RefreshTokenRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


async def _issue_tokens(user: User, refresh_tokens: RefreshTokenRepository) -> TokenPairOut:
    """Build a pair and persist the refresh token fingerprint for later revocation."""
    access = create_token(user.id, user.role, "access", settings.access_token_ttl)
    refresh = create_token(user.id, user.role, "refresh", settings.refresh_token_ttl)
    expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
        seconds=settings.refresh_token_ttl
    )
    await refresh_tokens.add(user.id, token_fingerprint(refresh), expires_at)
    return TokenPairOut(access_token=access, refresh_token=refresh)


async def _send_verification(user: User) -> None:
    token = create_token(user.id, user.role, "verify", settings.verification_token_ttl)
    try:
        await send_verification_email(user.email, token)
    except Exception:  # noqa: BLE001 - a mail outage must not lose the account
        logger.exception("could not send the verification email to %s", user.email)


@router.post("/register", response_model=UserOut, status_code=201)
async def register_account(payload: RegisterIn, users: UserRepo, session: DbSession) -> UserOut:
    """Create an account, then send an email-confirmation link."""
    try:
        user = await register(users, payload.email, payload.password, payload.display_name)
    except EmailAlreadyUsed as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except DomainError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    await session.commit()
    await _send_verification(user)
    return UserOut.from_user(user)


@router.post("/login", response_model=TokenPairOut)
async def login(
    payload: LoginIn, users: UserRepo, refresh_tokens: RefreshRepo, session: DbSession
) -> TokenPairOut:
    """Return an access/refresh pair for valid credentials."""
    try:
        user = await authenticate(users, payload.email, payload.password)
    except InvalidCredentials:
        raise HTTPException(status_code=401, detail="Invalid email or password") from None
    pair = await _issue_tokens(user, refresh_tokens)
    await session.commit()
    return pair


@router.post("/refresh", response_model=TokenPairOut)
async def refresh(
    payload: RefreshIn,
    users: UserRepo,
    refresh_tokens: RefreshRepo,
    session: DbSession,
) -> TokenPairOut:
    """Rotate a valid, unrevoked refresh token into a fresh pair."""
    try:
        claims = decode_token(payload.refresh_token, "refresh")
    except InvalidToken:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from None
    fingerprint = token_fingerprint(payload.refresh_token)
    record = await refresh_tokens.get(fingerprint)
    if record is None or record.revoked:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = await users.get_by_id(claims.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    await refresh_tokens.revoke(fingerprint)
    pair = await _issue_tokens(user, refresh_tokens)
    await session.commit()
    return pair


@router.post("/logout", status_code=204)
async def logout(payload: LogoutIn, refresh_tokens: RefreshRepo, session: DbSession) -> None:
    """Revoke the presented refresh token (idempotent, never leaks whether it existed)."""
    await refresh_tokens.revoke(token_fingerprint(payload.refresh_token))
    await session.commit()


@router.post("/verify-email", response_model=UserOut)
async def verify_email(payload: VerifyEmailIn, users: UserRepo, session: DbSession) -> UserOut:
    """Confirm an address from the token sent at registration or on resend."""
    try:
        claims = decode_token(payload.token, "verify")
    except InvalidToken:
        raise HTTPException(status_code=401, detail="Invalid verification token") from None
    user = await users.mark_email_verified(claims.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid verification token")
    await session.commit()
    return UserOut.from_user(user)


@router.post("/resend-verification", response_model=StatusOut, status_code=202)
async def resend_verification(user: CurrentUser) -> StatusOut:
    """Send a fresh confirmation link to an authenticated, unverified account."""
    if user.email_verified:
        raise HTTPException(status_code=409, detail="Email already verified")
    await _send_verification(user)
    return StatusOut(status="sent")


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    """Return the account behind the access token."""
    return UserOut.from_user(user)
