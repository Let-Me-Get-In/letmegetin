"""Use case: list official labels / complementary information."""

from __future__ import annotations

from letmegetin.domain.referential.entities import OtherInformation
from letmegetin.domain.referential.repositories import OtherInformationRepository


async def list_other_information(
    repository: OtherInformationRepository,
) -> list[OtherInformation]:
    """Return every official label, ordered by name."""
    return await repository.list_all()
