"""SQLAlchemy implementation of the ``LicenceRepository`` port.

Kept beside, not inside, ``repositories.py``: the licence surface is small and the
monolithic module already carries every other context.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from letmegetin.domain.referential.entities import Licence, LicenceDestination, SourceLicence
from letmegetin.infrastructure.persistence.models import (
    LicenceDestinationModel,
    LicenceModel,
    SourceLicenceModel,
)


class SqlAlchemyLicenceRepository:
    """Upserts (never deletes) the reviewed licence catalogue, matrix and source mapping."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_slug(self, slug: str) -> Licence | None:
        model = await self._session.get(LicenceModel, slug)
        if model is None:
            return None
        return Licence(
            slug=model.slug, name=model.name, url=model.url, obligations=list(model.obligations)
        )

    async def list_licences(self) -> list[Licence]:
        models = (
            await self._session.scalars(select(LicenceModel).order_by(LicenceModel.slug))
        ).all()
        return [
            Licence(
                slug=model.slug,
                name=model.name,
                url=model.url,
                obligations=list(model.obligations),
            )
            for model in models
        ]

    async def list_destinations(self, licence_slug: str | None = None) -> list[LicenceDestination]:
        statement = select(LicenceDestinationModel).order_by(
            LicenceDestinationModel.destination, LicenceDestinationModel.licence_slug
        )
        if licence_slug is not None:
            statement = statement.where(LicenceDestinationModel.licence_slug == licence_slug)
        models = (await self._session.scalars(statement)).all()
        return [
            LicenceDestination(
                licence_slug=model.licence_slug,
                destination=model.destination,
                allowed=model.allowed,
                note=model.note,
            )
            for model in models
        ]

    async def list_source_licences(self) -> list[SourceLicence]:
        models = (
            await self._session.scalars(
                select(SourceLicenceModel).order_by(SourceLicenceModel.source)
            )
        ).all()
        return [
            SourceLicence(
                source=model.source,
                licence_slug=model.licence_slug,
                effective_from=model.effective_from,
            )
            for model in models
        ]

    async def allowed(self, licence_slug: str, destination: str) -> bool:
        """Fail closed: an absent pair, or a licence outside the matrix, is refused (D-15)."""
        value = await self._session.scalar(
            select(LicenceDestinationModel.allowed).where(
                LicenceDestinationModel.licence_slug == licence_slug,
                LicenceDestinationModel.destination == destination,
            )
        )
        return bool(value)

    async def upsert_licence(self, licence: Licence) -> None:
        values: dict[str, object] = {
            "slug": licence.slug,
            "name": licence.name,
            "url": licence.url,
            "obligations": licence.obligations,
        }
        statement = insert(LicenceModel).values(**values)
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=[LicenceModel.slug],
                set_={key: value for key, value in values.items() if key != "slug"},
            )
        )

    async def upsert_destination(self, row: LicenceDestination) -> None:
        values: dict[str, object] = {
            "licence_slug": row.licence_slug,
            "destination": row.destination,
            "allowed": row.allowed,
            "note": row.note,
        }
        statement = insert(LicenceDestinationModel).values(**values)
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=[
                    LicenceDestinationModel.licence_slug,
                    LicenceDestinationModel.destination,
                ],
                set_={"allowed": statement.excluded.allowed, "note": statement.excluded.note},
            )
        )

    async def upsert_source_licence(self, row: SourceLicence) -> None:
        values: dict[str, object] = {
            "source": row.source,
            "licence_slug": row.licence_slug,
            "effective_from": row.effective_from,
        }
        statement = insert(SourceLicenceModel).values(**values)
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=[SourceLicenceModel.source],
                set_={
                    "licence_slug": statement.excluded.licence_slug,
                    "effective_from": statement.excluded.effective_from,
                },
            )
        )
