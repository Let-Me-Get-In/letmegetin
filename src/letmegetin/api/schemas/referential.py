"""Pydantic response schemas exposed by the referential API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    """A place category."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    label: dict[str, str]


class CriterionOut(BaseModel):
    """A node of the accessibility criteria tree."""

    slug: str
    label: dict[str, str]
    description: dict[str, str] = {}
    type: str
    children: list[CriterionOut] = []


class FilterOut(BaseModel):
    """A search filter."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    label: dict[str, str]
    position: int


class OtherInformationOut(BaseModel):
    """An official label / complementary information."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    label: dict[str, str]
    link: str | None = None
