"""Schémas Pydantic exposés par l'API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    """Catégorie de lieu."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    label: dict[str, str]


class CriterionOut(BaseModel):
    """Nœud de l'arbre d'accessibilité."""

    slug: str
    label: dict[str, str]
    description: dict[str, str] = {}
    type: str
    children: list[CriterionOut] = []


class FilterOut(BaseModel):
    """Filtre de recherche."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    label: dict[str, str]
    position: int


class OtherInformationOut(BaseModel):
    """Label officiel / information complémentaire."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    label: dict[str, str]
    link: str | None = None
