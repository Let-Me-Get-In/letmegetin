"""Load the reconstructed seed into PostgreSQL/PostGIS.

The schema must exist first: `uv run alembic upgrade head`.
Usage: `uv run python -m letmegetin.seed`
Idempotent: existing rows are not duplicated.
"""

from __future__ import annotations

import asyncio
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from letmegetin.config import settings
from letmegetin.core.db import SessionLocal
from letmegetin.core.utils import slugify
from letmegetin.infrastructure.persistence.models import (
    AccessibilityFilterModel,
    CategoryCriterionModel,
    CategoryModel,
    CriterionModel,
    OtherInformationModel,
)


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
) -> CriterionModel:
    existing = await session.scalar(select(CriterionModel).where(CriterionModel.slug == slug))
    if existing is not None:
        return existing
    criterion = CriterionModel(
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
    """Insert categories, filters, labels and the category-1 grid (schema already migrated)."""
    data_dir = settings.data_dir
    async with SessionLocal() as session:
        for entry in json.loads((data_dir / "categories.json").read_text(encoding="utf-8")):
            exists = await session.scalar(
                select(CategoryModel).where(CategoryModel.slug == entry["slug"])
            )
            if exists is None:
                session.add(
                    CategoryModel(slug=entry["slug"], name=entry["name"], label=entry["label"])
                )

        for position, entry in enumerate(
            json.loads((data_dir / "filters.json").read_text(encoding="utf-8"))
        ):
            exists = await session.scalar(
                select(AccessibilityFilterModel).where(
                    AccessibilityFilterModel.slug == entry["slug"]
                )
            )
            if exists is None:
                session.add(
                    AccessibilityFilterModel(
                        slug=entry["slug"], label=entry["label"], position=position
                    )
                )

        for entry in json.loads((data_dir / "th.json").read_text(encoding="utf-8")):
            exists = await session.scalar(
                select(OtherInformationModel).where(OtherInformationModel.slug == entry["slug"])
            )
            if exists is None:
                session.add(
                    OtherInformationModel(
                        slug=entry["slug"], name=entry["name"], label=entry["label"]
                    )
                )

        await session.flush()

        grid = json.loads(
            (data_dir / "category_grids" / "category-1.json").read_text(encoding="utf-8")
        )
        linked_ids: list[int] = []
        for group_index, group in enumerate(grid):
            group_name = group.get("name") or f"Group {group_index + 1}"
            group_slug = slugify(group_name)
            group_node = await _upsert_criterion(
                session, group_slug, None, "array", group_index, {"fr": group_name}
            )
            for criterion_index, criterion in enumerate(group.get("criteria", [])):
                criterion_name = criterion.get("name") or f"Criterion {criterion_index + 1}"
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

        categories = list((await session.scalars(select(CategoryModel))).all())
        for category in categories:
            for criterion_id in linked_ids:
                exists = await session.scalar(
                    select(CategoryCriterionModel).where(
                        CategoryCriterionModel.category_id == category.id,
                        CategoryCriterionModel.criterion_id == criterion_id,
                    )
                )
                if exists is None:
                    session.add(
                        CategoryCriterionModel(category_id=category.id, criterion_id=criterion_id)
                    )

        await session.commit()
        print(f"seed ok: categories={len(categories)} base_criteria={len(linked_ids)}")


if __name__ == "__main__":
    asyncio.run(seed())
