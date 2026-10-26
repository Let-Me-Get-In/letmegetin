"""Charge le seed reconstitué dans PostgreSQL/PostGIS.

Usage : `uv run python -m letmegetin.seed`
Idempotent : les enregistrements existants ne sont pas dupliqués.
"""

from __future__ import annotations

import asyncio
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from letmegetin.config import settings
from letmegetin.db import SessionLocal, engine
from letmegetin.models import (
    AccessibilityFilter,
    Base,
    Category,
    CategoryCriterion,
    Criterion,
    OtherInformation,
)
from letmegetin.utils import slugify


def _criterion_type(data: dict) -> str:
    if data.get("type") == "user_value":
        return "integer" if "(cm)" in (data.get("name") or "") else "string"
    if data.get("options"):
        return "option"
    return "boolean"


async def _upsert_criterion(
    session: AsyncSession,
    slug: str,
    parent_id: int | None,
    kind: str,
    position: int,
    label: dict[str, str],
    description: dict[str, str] | None = None,
) -> Criterion:
    existing = await session.scalar(select(Criterion).where(Criterion.slug == slug))
    if existing is not None:
        return existing
    criterion = Criterion(
        slug=slug,
        parent_id=parent_id,
        type=kind,
        position=position,
        label=label,
        description=description or {},
    )
    session.add(criterion)
    await session.flush()
    return criterion


async def seed() -> None:
    """Crée le schéma puis insère catégories, filtres, labels et grille catégorie 1."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    data_dir = settings.data_dir
    async with SessionLocal() as session:
        for entry in json.loads((data_dir / "categories.json").read_text(encoding="utf-8")):
            exists = await session.scalar(select(Category).where(Category.slug == entry["slug"]))
            if exists is None:
                session.add(Category(slug=entry["slug"], name=entry["name"], label=entry["label"]))

        for position, entry in enumerate(
            json.loads((data_dir / "filters.json").read_text(encoding="utf-8"))
        ):
            exists = await session.scalar(
                select(AccessibilityFilter).where(AccessibilityFilter.slug == entry["slug"])
            )
            if exists is None:
                session.add(
                    AccessibilityFilter(slug=entry["slug"], label=entry["label"], position=position)
                )

        for entry in json.loads((data_dir / "th.json").read_text(encoding="utf-8")):
            exists = await session.scalar(
                select(OtherInformation).where(OtherInformation.slug == entry["slug"])
            )
            if exists is None:
                session.add(
                    OtherInformation(slug=entry["slug"], name=entry["name"], label=entry["label"])
                )

        await session.flush()

        grid = json.loads(
            (data_dir / "category_grids" / "category-1.json").read_text(encoding="utf-8")
        )
        linked_ids: list[int] = []
        for group_index, group in enumerate(grid):
            group_name = group.get("name") or f"Groupe {group_index + 1}"
            group_slug = slugify(group_name)
            group_node = await _upsert_criterion(
                session, group_slug, None, "array", group_index, {"fr": group_name}
            )
            for criterion_index, criterion in enumerate(group.get("criteria", [])):
                criterion_name = criterion.get("name") or f"Critère {criterion_index + 1}"
                criterion_slug = f"{group_slug}-{slugify(criterion_name)}"
                criterion_node = await _upsert_criterion(
                    session,
                    criterion_slug,
                    group_node.id,
                    _criterion_type(criterion),
                    criterion_index,
                    {"fr": criterion_name},
                    {"fr": criterion.get("description") or ""},
                )
                linked_ids.append(criterion_node.id)
                for option_index, option in enumerate(criterion.get("options", [])):
                    label = (
                        option.get("label") or option.get("value") or f"Option {option_index + 1}"
                    )
                    await _upsert_criterion(
                        session,
                        f"{criterion_slug}-{slugify(label)}",
                        criterion_node.id,
                        "option",
                        option_index,
                        {"fr": label},
                    )

        categories = list((await session.scalars(select(Category))).all())
        for category in categories:
            for criterion_id in linked_ids:
                exists = await session.scalar(
                    select(CategoryCriterion).where(
                        CategoryCriterion.category_id == category.id,
                        CategoryCriterion.criterion_id == criterion_id,
                    )
                )
                if exists is None:
                    session.add(
                        CategoryCriterion(category_id=category.id, criterion_id=criterion_id)
                    )

        await session.commit()
        print(f"seed ok: categories={len(categories)} base_criteria={len(linked_ids)}")


if __name__ == "__main__":
    asyncio.run(seed())
