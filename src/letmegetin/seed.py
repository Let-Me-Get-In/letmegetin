"""Load the reconstructed seed into PostgreSQL/PostGIS.

The schema must exist first: `uv run alembic upgrade head`.
Usage: `uv run python -m letmegetin.seed`
Idempotent: existing rows are not duplicated.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from letmegetin.application.referential.admin import load_vocabulary_file
from letmegetin.config import settings
from letmegetin.core.db import SessionLocal
from letmegetin.core.utils import slugify
from letmegetin.infrastructure.persistence.models import (
    AccessibilityFilterModel,
    CategoryModel,
    CriterionModel,
    CriterionVocabularyModel,
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
    *,
    is_default: bool = False,
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
        is_default=is_default,
    )
    session.add(criterion)
    await session.flush()
    return criterion


async def _load_vocabulary(session: AsyncSession, path: Path) -> tuple[int, int]:
    created = 0
    skipped = 0
    for entry in load_vocabulary_file(path):
        exists = await session.scalar(
            select(CriterionVocabularyModel).where(CriterionVocabularyModel.slug == entry.slug)
        )
        if exists is not None:
            skipped += 1
            continue
        session.add(
            CriterionVocabularyModel(
                slug=entry.slug, label=entry.label, description=entry.description
            )
        )
        created += 1
    return created, skipped


async def seed() -> None:
    """Insert categories, filters, labels, the vocabulary and the category-1 grid."""
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

        vocabulary_created, vocabulary_skipped = await _load_vocabulary(
            session, data_dir / "criteria.json"
        )

        grid = json.loads(
            (data_dir / "category_grids" / "category-1.json").read_text(encoding="utf-8")
        )
        base_criteria = 0
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
                    is_default=True,
                )
                base_criteria += 1
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

        await session.commit()
        print(
            f"seed ok: categories={len(categories)} base_criteria={base_criteria} "
            f"vocabulary_created={vocabulary_created} vocabulary_skipped={vocabulary_skipped}"
        )


if __name__ == "__main__":
    asyncio.run(seed())
