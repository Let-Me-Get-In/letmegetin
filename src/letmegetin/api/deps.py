"""FastAPI dependencies wired to the infrastructure adapters."""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Response
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from letmegetin.config import settings
from letmegetin.core.db import get_session
from letmegetin.core.exceptions import InvalidToken
from letmegetin.core.metrics import RATE_LIMITED
from letmegetin.core.rate_limit import check_rate_limit
from letmegetin.core.security import decode_token, token_fingerprint
from letmegetin.domain.accounts.entities import User
from letmegetin.domain.accounts.repositories import RefreshTokenRepository, UserRepository
from letmegetin.domain.places.repositories import PlaceRepository
from letmegetin.domain.referential.repositories import (
    CategoryGridRepository,
    CategoryRepository,
    CriterionRepository,
    FilterRepository,
    OtherInformationRepository,
)
from letmegetin.infrastructure.persistence.repositories import (
    SqlAlchemyApiKeyRepository,
    SqlAlchemyCategoryGridRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyCriterionRepository,
    SqlAlchemyFilterRepository,
    SqlAlchemyOtherInformationRepository,
    SqlAlchemyPlaceRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyUserRepository,
)

DbSession = Annotated[AsyncSession, Depends(get_session)]


def get_category_repository(session: DbSession) -> CategoryRepository:
    return SqlAlchemyCategoryRepository(session)


def get_criterion_repository(session: DbSession) -> CriterionRepository:
    return SqlAlchemyCriterionRepository(session)


def get_filter_repository(session: DbSession) -> FilterRepository:
    return SqlAlchemyFilterRepository(session)


def get_other_information_repository(session: DbSession) -> OtherInformationRepository:
    return SqlAlchemyOtherInformationRepository(session)


def get_place_repository(session: DbSession) -> PlaceRepository:
    return SqlAlchemyPlaceRepository(session)


def get_category_grid_repository(session: DbSession) -> CategoryGridRepository:
    return SqlAlchemyCategoryGridRepository(session)


def get_user_repository(session: DbSession) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_refresh_token_repository(session: DbSession) -> RefreshTokenRepository:
    return SqlAlchemyRefreshTokenRepository(session)


async def get_current_user(
    session: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Resolve the bearer token to an account, or fail with 401."""
    unauthorized = HTTPException(
        status_code=401,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise unauthorized
    try:
        payload = decode_token(authorization.split(" ", 1)[1], "access")
    except InvalidToken:
        raise unauthorized from None
    user = await SqlAlchemyUserRepository(session).get_by_id(payload.user_id)
    if user is None:
        raise unauthorized
    return user


def require_admin(user: CurrentUser) -> User:
    """Reject any authenticated user whose role is not ``admin``."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


def require_verified(user: CurrentUser) -> User:
    """Reject writes from an account whose email is not confirmed yet."""
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Email verification required")
    return user


CategoryRepo = Annotated[CategoryRepository, Depends(get_category_repository)]
CriterionRepo = Annotated[CriterionRepository, Depends(get_criterion_repository)]
FilterRepo = Annotated[FilterRepository, Depends(get_filter_repository)]
OtherInformationRepo = Annotated[
    OtherInformationRepository, Depends(get_other_information_repository)
]
PlaceRepo = Annotated[PlaceRepository, Depends(get_place_repository)]
CategoryGridRepo = Annotated[CategoryGridRepository, Depends(get_category_grid_repository)]
UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
RefreshRepo = Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
VerifiedUser = Annotated[User, Depends(require_verified)]


_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _client_ip(request: Request) -> str:
    """The real client IP behind Caddy (the API is not publicly reachable)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limit_dependency(default_setting: str):
    async def dependency(
        request: Request,
        response: Response,
        session: DbSession,
        api_key: Annotated[str | None, Depends(_api_key_header)] = None,
    ) -> None:
        key_row = None
        if api_key:
            key_row = await SqlAlchemyApiKeyRepository(session).get_by_hash(
                token_fingerprint(api_key)
            )
            if key_row is None or not key_row.active:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid API key",
                    headers={"WWW-Authenticate": "ApiKey"},
                )
        limit = key_row.rpm if key_row is not None else int(getattr(settings, default_setting))
        bucket = f"key:{key_row.id}" if key_row is not None else f"ip:{_client_ip(request)}"
        result = await check_rate_limit(bucket, limit)
        reset_at = str(int(time.time()) + result.retry_after)
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = reset_at
        if not result.allowed:
            RATE_LIMITED.inc()
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={
                    "Retry-After": str(result.retry_after),
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": reset_at,
                },
            )

    return dependency


public_rate_limit = _rate_limit_dependency("rate_limit_default_rpm")
auth_rate_limit = _rate_limit_dependency("rate_limit_auth_rpm")
