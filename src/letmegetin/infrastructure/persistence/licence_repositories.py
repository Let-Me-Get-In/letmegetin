"""SQLAlchemy implementation of the ``LicenceRepository`` port.

Kept beside, not inside, ``repositories.py``: the licence surface is small and the
monolithic module already carries every other context.
"""

from __future__ import annotations

from sqlalchemy import and_, exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from letmegetin.domain.referential.entities import Licence, LicenceDestination, SourceLicence
from letmegetin.infrastructure.persistence.models import (
    LicenceDestinationModel,
    LicenceModel,
    PlaceModel,
    SourceLicenceModel,
)


def _may_leave(destination: str) -> ColumnElement[bool]:
    """The SQL twin of ``can_redistribute``: an allowed matrix row for the row's own licence.

    Correlation is on ``place.source_license``, so a NULL or unknown licence matches
    nothing — fail-closed, like the domain predicate (D-13, D-15). ``destination`` is a
    bound parameter, never interpolated (T-12-04).
    """
    return exists(
        select(1).where(
            LicenceDestinationModel.licence_slug == PlaceModel.source_license,
            LicenceDestinationModel.destination == destination,
            LicenceDestinationModel.allowed.is_(True),
        )
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

    async def redistributable_place_ids(self, destination: str) -> list[int]:
        """Bulk twin of ``can_redistribute``: only rows the matrix lets leave (D-13).

        The join carries the rule, so a NULL licence, an unknown licence and a denied
        row all match nothing — the export path never re-implements the check.
        """
        statement = (
            select(PlaceModel.id)
            .join(
                LicenceDestinationModel,
                and_(
                    LicenceDestinationModel.licence_slug == PlaceModel.source_license,
                    LicenceDestinationModel.destination == destination,
                    LicenceDestinationModel.allowed.is_(True),
                ),
            )
            .order_by(PlaceModel.id)
        )
        return list((await self._session.scalars(statement)).all())

    async def exclusion_counts(self, destination: str) -> list[tuple[str, str | None, int]]:
        """Per ``(source, licence)`` counts of the places a destination leaves out (D-14)."""
        statement = (
            select(PlaceModel.source, PlaceModel.source_license, func.count(PlaceModel.id))
            .where(~_may_leave(destination))
            .group_by(PlaceModel.source, PlaceModel.source_license)
            .order_by(PlaceModel.source, PlaceModel.source_license)
        )
        found = (await self._session.execute(statement)).all()
        return [(str(source), licence, int(count)) for source, licence, count in found]

    async def excluded_ids(self, destination: str) -> list[tuple[int, str | None]]:
        """The place ids — with their licence — a destination cannot take (D-14)."""
        statement = (
            select(PlaceModel.id, PlaceModel.source_license)
            .where(~_may_leave(destination))
            .order_by(PlaceModel.id)
        )
        found = (await self._session.execute(statement)).all()
        return [(int(place_id), licence) for place_id, licence in found]
