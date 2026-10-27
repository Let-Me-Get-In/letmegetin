"""FastAPI dependencies wired to the infrastructure adapters."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from letmegetin.core.db import get_session
from letmegetin.domain.places.repositories import PlaceRepository
from letmegetin.domain.referential.repositories import (
    CategoryRepository,
    CriterionRepository,
    FilterRepository,
    OtherInformationRepository,
)
from letmegetin.infrastructure.persistence.repositories import (
    SqlAlchemyCategoryRepository,
    SqlAlchemyCriterionRepository,
    SqlAlchemyFilterRepository,
    SqlAlchemyOtherInformationRepository,
    SqlAlchemyPlaceRepository,
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


CategoryRepo = Annotated[CategoryRepository, Depends(get_category_repository)]
CriterionRepo = Annotated[CriterionRepository, Depends(get_criterion_repository)]
FilterRepo = Annotated[FilterRepository, Depends(get_filter_repository)]
OtherInformationRepo = Annotated[
    OtherInformationRepository, Depends(get_other_information_repository)
]
PlaceRepo = Annotated[PlaceRepository, Depends(get_place_repository)]
