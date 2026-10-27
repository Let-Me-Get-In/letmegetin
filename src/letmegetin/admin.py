"""Operator CLI: the only write path to the referential (no HTTP surface, no auth yet).

Usage: ``uv run python -m letmegetin.admin --help`` or ``uv run letmegetin-admin``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated

import typer
from sqlalchemy.ext.asyncio import AsyncSession

from letmegetin.application.referential.admin import import_vocabulary, load_vocabulary_file
from letmegetin.config import settings
from letmegetin.core.db import SessionLocal
from letmegetin.core.exceptions import DomainError
from letmegetin.infrastructure.persistence.repositories import (
    SqlAlchemyVocabularyRepository,
)

app = typer.Typer(help="Curate the accessibility referential.")
vocabulary_app = typer.Typer(help="Import, list and promote the flat criteria vocabulary.")
app.add_typer(vocabulary_app, name="vocabulary")

AdminCallback = Callable[[AsyncSession], Awaitable[str]]


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


@vocabulary_app.command("import")
def import_(
    file: Annotated[Path | None, typer.Option("--file", "-f")] = None,
) -> None:
    """Import the flat vocabulary JSON into criterion_vocabulary (skips known slugs)."""
    path = file or settings.data_dir / "criteria.json"

    async def callback(session: AsyncSession) -> str:
        repository = SqlAlchemyVocabularyRepository(session)
        report = await import_vocabulary(repository, load_vocabulary_file(path))
        return f"vocabulary import: created={report.created} skipped={report.skipped}"

    _run_admin(callback)


if __name__ == "__main__":
    app()
