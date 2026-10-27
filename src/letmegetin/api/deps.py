"""FastAPI dependencies wired to the infrastructure adapters."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from letmegetin.core.db import get_session
from letmegetin.core.exceptions import InvalidToken
from letmegetin.core.security import decode_token
from letmegetin.domain.accounts.entities import User
from letmegetin.domain.accounts.repositories import UserRepository
from letmegetin.domain.places.repositories import PlaceRepository
from letmegetin.domain.referential.repositories import (
    CategoryGridRepository,
    CategoryRepository,
    CriterionRepository,
    FilterRepository,
    OtherInformationRepository,
)
from letmegetin.infrastructure.persistence.repositories import (
    SqlAlchemyCategoryGridRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyCriterionRepository,
    SqlAlchemyFilterRepository,
    SqlAlchemyOtherInformationRepository,
    SqlAlchemyPlaceRepository,
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


CategoryRepo = Annotated[CategoryRepository, Depends(get_category_repository)]
CriterionRepo = Annotated[CriterionRepository, Depends(get_criterion_repository)]
FilterRepo = Annotated[FilterRepository, Depends(get_filter_repository)]
OtherInformationRepo = Annotated[
    OtherInformationRepository, Depends(get_other_information_repository)
]
PlaceRepo = Annotated[PlaceRepository, Depends(get_place_repository)]
CategoryGridRepo = Annotated[CategoryGridRepository, Depends(get_category_grid_repository)]
UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
