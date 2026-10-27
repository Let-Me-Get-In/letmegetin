"""Operator CLI: the only write path to the referential (no HTTP surface, no auth yet).

Usage: ``uv run python -m letmegetin.admin --help`` or ``uv run letmegetin-admin``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated, Literal

import typer
from sqlalchemy.ext.asyncio import AsyncSession

from letmegetin.application.referential.admin import (
    add_category,
    add_criterion,
    edit_category,
    edit_criterion,
    import_vocabulary,
    link_criterion,
    load_vocabulary_file,
    promote_vocabulary,
    set_category_labels,
    set_criterion_labels,
    set_vocabulary_labels,
    unlink_criterion,
)
from letmegetin.config import settings
from letmegetin.core.db import SessionLocal
from letmegetin.core.exceptions import CategoryNotFound, DomainError
from letmegetin.domain.referential.entities import Category, Criterion, Label, VocabularyEntry
from letmegetin.domain.referential.labels import parse_label_pairs
from letmegetin.infrastructure.persistence.repositories import (
    SqlAlchemyCategoryRepository,
    SqlAlchemyCriterionRepository,
    SqlAlchemyMappingRepository,
    SqlAlchemyVocabularyRepository,
)

app = typer.Typer(help="Curate the accessibility referential.")
category_app = typer.Typer(help="Add, edit and list place categories.")
criterion_app = typer.Typer(help="Add, edit and list criteria and options.")
vocabulary_app = typer.Typer(help="Import, list and promote the flat criteria vocabulary.")
labels_app = typer.Typer(help="Set multilingual labels on any referential entity.")
app.add_typer(category_app, name="category")
app.add_typer(criterion_app, name="criterion")
app.add_typer(vocabulary_app, name="vocabulary")
app.add_typer(labels_app, name="labels")

AdminCallback = Callable[[AsyncSession], Awaitable[str]]
LabelPairs = Annotated[
    list[str] | None, typer.Option("--label", "-l", help="locale=value, repeatable")
]


def _run_admin(callback: AdminCallback) -> None:
    """Run a use case in one session, commit on success, and map domain errors to exit 1."""

    async def run() -> str:
        async with SessionLocal() as session:
            message = await callback(session)
            await session.commit()
            return message

    try:
        message = asyncio.run(run())
    except DomainError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(message)


def _labels(pairs: list[str] | None) -> Label:
    return parse_label_pairs(pairs or [])


@category_app.command("list")
def category_list() -> None:
    """List every category with its French label."""

    async def callback(session: AsyncSession) -> str:
        categories = await SqlAlchemyCategoryRepository(session).list_all()
        return "\n".join(f"{item.slug}\t{item.label.get('fr', item.name)}" for item in categories)

    _run_admin(callback)


@category_app.command("add")
def category_add(
    slug: Annotated[str, typer.Argument(help="Stable slug, e.g. restaurant")],
    name: Annotated[str, typer.Option("--name", "-n", help="Display name")],
    label: LabelPairs = None,
) -> None:
    """Create a category."""
    labels = _labels(label)

    async def callback(session: AsyncSession) -> str:
        category = await add_category(SqlAlchemyCategoryRepository(session), slug, name, labels)
        return f"category added: {category.slug}"

    _run_admin(callback)


@category_app.command("edit")
def category_edit(
    slug: Annotated[str, typer.Argument(help="Category slug")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="Display name")] = None,
    label: LabelPairs = None,
    parent: Annotated[str | None, typer.Option("--parent", help="Parent category slug")] = None,
) -> None:
    """Edit a category: labels are merged, never replaced."""
    labels = _labels(label)

    async def callback(session: AsyncSession) -> str:
        repository = SqlAlchemyCategoryRepository(session)
        category = await edit_category(repository, slug, name, labels, parent)
        return f"category edited: {category.slug}"

    _run_admin(callback)


@criterion_app.command("list")
def criterion_list(
    category: Annotated[str | None, typer.Option("--category", help="Category slug")] = None,
    flat: Annotated[bool, typer.Option("--flat", help="List every criterion, no tree")] = False,
) -> None:
    """List criteria, either the category tree, every row, or a flat dump."""

    async def callback(session: AsyncSession) -> str:
        criteria = SqlAlchemyCriterionRepository(session)
        if category is not None:
            found = await SqlAlchemyCategoryRepository(session).get_by_slug(category)
            if found is None:
                raise CategoryNotFound(category)
            rows = await criteria.list_for_category(found.id)
        else:
            rows = await criteria.list_all()
        if flat:
            return "\n".join(f"{row.slug}\t{row.type}" for row in rows)
        return "\n".join(
            f"{'  ' if row.parent_id else ''}{row.slug}\t{row.type}"
            f"{' [default]' if row.is_default else ''}"
            for row in rows
        )

    _run_admin(callback)


@criterion_app.command("add")
def criterion_add(
    slug: Annotated[str, typer.Argument(help="Criterion slug")],
    kind: Annotated[str, typer.Option("--type", help="array, option, boolean, integer, string")] = (
        "boolean"
    ),
    label: LabelPairs = None,
    parent: Annotated[str | None, typer.Option("--parent", help="Parent criterion slug")] = None,
    description: Annotated[
        list[str] | None,
        typer.Option("--description", help="locale=value, repeatable"),
    ] = None,
    default: Annotated[bool, typer.Option("--default/--no-default")] = False,
) -> None:
    """Create a criterion (an option is a criterion with --type option and --parent)."""
    labels = _labels(label)
    descriptions = _labels(description)

    async def callback(session: AsyncSession) -> str:
        criterion = await add_criterion(
            SqlAlchemyCriterionRepository(session),
            slug,
            kind,
            labels,
            parent,
            descriptions,
            default,
        )
        return f"criterion added: {criterion.slug}"

    _run_admin(callback)


@criterion_app.command("edit")
def criterion_edit(
    slug: Annotated[str, typer.Argument(help="Criterion slug")],
    kind: Annotated[str | None, typer.Option("--type", help="Criterion type")] = None,
    label: LabelPairs = None,
    parent: Annotated[str | None, typer.Option("--parent", help="Parent criterion slug")] = None,
    description: Annotated[
        list[str] | None,
        typer.Option("--description", help="locale=value, repeatable"),
    ] = None,
    default: Annotated[bool | None, typer.Option("--default/--no-default")] = None,
) -> None:
    """Edit a criterion: labels and descriptions are merged, never replaced."""
    labels = _labels(label)
    descriptions = _labels(description)

    async def callback(session: AsyncSession) -> str:
        criterion = await edit_criterion(
            SqlAlchemyCriterionRepository(session),
            slug,
            kind,
            labels,
            descriptions,
            default,
            parent,
        )
        return f"criterion edited: {criterion.slug}"

    _run_admin(callback)


@app.command("link")
def link(
    category_slug: Annotated[str, typer.Argument(help="Category slug")],
    criterion_slug: Annotated[str, typer.Argument(help="Criterion slug")],
) -> None:
    """Make a criterion apply to a category."""

    async def callback(session: AsyncSession) -> str:
        return await link_criterion(
            SqlAlchemyCategoryRepository(session),
            SqlAlchemyCriterionRepository(session),
            SqlAlchemyMappingRepository(session),
            category_slug,
            criterion_slug,
        )

    _run_admin(callback)


@app.command("unlink")
def unlink(
    category_slug: Annotated[str, typer.Argument(help="Category slug")],
    criterion_slug: Annotated[str, typer.Argument(help="Criterion slug")],
) -> None:
    """Stop a criterion applying to a category."""

    async def callback(session: AsyncSession) -> str:
        return await unlink_criterion(
            SqlAlchemyCategoryRepository(session),
            SqlAlchemyCriterionRepository(session),
            SqlAlchemyMappingRepository(session),
            category_slug,
            criterion_slug,
        )

    _run_admin(callback)


@vocabulary_app.command("import")
def import_(
    file: Annotated[Path | None, typer.Option("--file", "-f")] = None,
) -> None:
    """Import the flat vocabulary JSON into criterion_vocabulary (skips known slugs)."""
    path = file or settings.data_dir / "criteria.json"

    async def callback(session: AsyncSession) -> str:
        report = await import_vocabulary(
            SqlAlchemyVocabularyRepository(session), load_vocabulary_file(path)
        )
        return f"vocabulary import: created={report.created} skipped={report.skipped}"

    _run_admin(callback)


@vocabulary_app.command("list")
def vocabulary_list(
    query: Annotated[str | None, typer.Option("--query", help="Filter on slug or French label")] = (
        None
    ),
    unpromoted: Annotated[
        bool, typer.Option("--unpromoted", help="Only entries not yet promoted")
    ] = False,
) -> None:
    """List the vocabulary, optionally filtered."""

    async def callback(session: AsyncSession) -> str:
        entries = await SqlAlchemyVocabularyRepository(session).list_all()
        needle = (query or "").lower()
        rows = [
            entry
            for entry in entries
            if (not unpromoted or entry.promoted_criterion_id is None)
            and (not needle or needle in entry.slug or needle in entry.label.get("fr", "").lower())
        ]
        return "\n".join(
            f"{entry.slug}\t{entry.label.get('fr', '')}"
            f"{' -> ' + str(entry.promoted_criterion_id) if entry.promoted_criterion_id else ''}"
            for entry in rows
        )

    _run_admin(callback)


@vocabulary_app.command("promote")
def vocabulary_promote(
    slug: Annotated[str, typer.Argument(help="Vocabulary slug")],
    kind: Annotated[str, typer.Option("--type", help="Criterion type")] = "boolean",
    parent: Annotated[str | None, typer.Option("--parent", help="Parent criterion slug")] = None,
    category: Annotated[
        list[str] | None, typer.Option("--category", help="Category slug, repeatable")
    ] = None,
) -> None:
    """Turn a vocabulary entry into a criterion and link it to categories."""

    async def callback(session: AsyncSession) -> str:
        criterion = await promote_vocabulary(
            SqlAlchemyVocabularyRepository(session),
            SqlAlchemyCriterionRepository(session),
            SqlAlchemyMappingRepository(session),
            SqlAlchemyCategoryRepository(session),
            slug,
            kind,
            parent,
            category or [],
        )
        return f"vocabulary promoted: {slug} -> {criterion.slug}"

    _run_admin(callback)


@labels_app.command("set")
def labels_set(
    kind: Annotated[Literal["category", "criterion", "vocabulary"], typer.Argument()],
    slug: Annotated[str, typer.Argument(help="Slug of the addressed entity")],
    label: LabelPairs = None,
) -> None:
    """Merge a label map onto a category, criterion or vocabulary entry."""
    labels = _labels(label)

    async def callback(session: AsyncSession) -> str:
        entity: Category | Criterion | VocabularyEntry
        if kind == "category":
            entity = await set_category_labels(SqlAlchemyCategoryRepository(session), slug, labels)
        elif kind == "criterion":
            entity = await set_criterion_labels(
                SqlAlchemyCriterionRepository(session), slug, labels
            )
        else:
            entity = await set_vocabulary_labels(
                SqlAlchemyVocabularyRepository(session), slug, labels
            )
        return f"{kind} labels set: {entity.slug} {entity.label}"

    _run_admin(callback)


if __name__ == "__main__":
    app()
