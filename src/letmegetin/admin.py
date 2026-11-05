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

from letmegetin.application.accounts.api_keys import (
    create_api_key,
    list_api_keys,
    revoke_api_key,
)
from letmegetin.application.places.category_resolution import load_category_aliases
from letmegetin.application.places.coverage import (
    COVERAGE_HEADER,
    coverage,
    coverage_csv,
    coverage_table,
)
from letmegetin.application.places.duplicates import (
    in_review_band,
    list_pending,
    merge_duplicate,
    reject_duplicate,
)
from letmegetin.application.places.import_acceslibre import (
    import_acceslibre,
    iter_acceslibre_rows,
)
from letmegetin.application.referential.admin import (
    add_category,
    add_criterion,
    edit_category,
    edit_criterion,
    import_vocabulary,
    link_criterion,
    load_vocabulary_file,
    map_category,
    promote_vocabulary,
    rebuild_category_grids,
    set_category_labels,
    set_criterion_families,
    set_criterion_labels,
    set_vocabulary_labels,
    unlink_criterion,
)
from letmegetin.application.referential.families import (
    apply_families,
    audit_families,
    load_families,
)
from letmegetin.application.retention import run_retention
from letmegetin.config import settings
from letmegetin.core.db import SessionLocal
from letmegetin.core.exceptions import CategoryNotFound, DomainError
from letmegetin.domain.referential.entities import Category, Criterion, Label, VocabularyEntry
from letmegetin.domain.referential.labels import parse_label_pairs
from letmegetin.infrastructure.persistence.repositories import (
    SqlAlchemyApiKeyRepository,
    SqlAlchemyCategoryGridRepository,
    SqlAlchemyCategoryMappingRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyCoverageRepository,
    SqlAlchemyCriterionRepository,
    SqlAlchemyFilterRepository,
    SqlAlchemyMappingRepository,
    SqlAlchemyMergeLogRepository,
    SqlAlchemyPlaceAliasRepository,
    SqlAlchemyPlaceRepository,
    SqlAlchemyRetentionRepository,
    SqlAlchemyVocabularyRepository,
)

app = typer.Typer(help="Curate the accessibility referential.")
category_app = typer.Typer(help="Add, edit and list place categories.")
criterion_app = typer.Typer(help="Add, edit and list criteria and options.")
vocabulary_app = typer.Typer(help="Import, list and promote the flat criteria vocabulary.")
labels_app = typer.Typer(help="Set multilingual labels on any referential entity.")
families_app = typer.Typer(help="Fill and audit handicap families (moteur, auditif, visuel…).")
import_app = typer.Typer(help="Import open place datasets (Acceslibre first).")
duplicates_app = typer.Typer(help="Review, merge or reject duplicate candidates from the import.")
api_key_app = typer.Typer(help="Create, list and revoke partner API keys.")
app.add_typer(category_app, name="category")
app.add_typer(criterion_app, name="criterion")
app.add_typer(vocabulary_app, name="vocabulary")
app.add_typer(labels_app, name="labels")
app.add_typer(families_app, name="families")
app.add_typer(import_app, name="import")
app.add_typer(duplicates_app, name="duplicates")
app.add_typer(api_key_app, name="api-key")

AdminCallback = Callable[[AsyncSession], Awaitable[str]]
LabelPairs = Annotated[
    list[str] | None, typer.Option("--label", "-l", help="locale=value, repeatable")
]


def _run_admin(callback: AdminCallback, *, bump: bool = True, commit: bool = True) -> None:
    """Run a use case in one session, commit on success, and map domain errors to exit 1.

    Any write bumps the referential version and recomputes the grids, so clients refetch
    their cached grid only when it actually changed. ``commit=False`` rolls back, which is
    what a dry run needs.
    """

    async def run() -> str:
        async with SessionLocal() as session:
            message = await callback(session)
            if bump:
                await rebuild_category_grids(
                    SqlAlchemyCategoryRepository(session),
                    SqlAlchemyCriterionRepository(session),
                    SqlAlchemyCategoryGridRepository(session),
                )
            if commit:
                await session.commit()
            else:
                await session.rollback()
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

    _run_admin(callback, bump=False)


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


@category_app.command("map")
def category_map(
    slug: Annotated[str, typer.Argument(help="Category slug")],
    overture: Annotated[str | None, typer.Option("--overture", help="Overture basic_category")] = (
        None
    ),
    osm: Annotated[str | None, typer.Option("--osm", help="OSM tag, e.g. amenity=restaurant")] = (
        None
    ),
    acceslibre: Annotated[
        str | None, typer.Option("--acceslibre", help="Acceslibre family")
    ] = None,
    notes: Annotated[str | None, typer.Option("--notes", help="Free-form note")] = None,
) -> None:
    """Map a category to the Overture, OSM and Acceslibre vocabularies."""

    async def callback(session: AsyncSession) -> str:
        category = await map_category(
            SqlAlchemyCategoryMappingRepository(session),
            SqlAlchemyCategoryRepository(session),
            slug,
            overture,
            osm,
            acceslibre,
            notes,
        )
        return f"category mapped: {category.slug}"

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

    _run_admin(callback, bump=False)


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
    family: Annotated[
        list[str] | None,
        typer.Option("--family", help="moteur, auditif, visuel, mental — repeatable"),
    ] = None,
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
            families=family,
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
    en17210: Annotated[
        str | None, typer.Option("--en17210", help="EN 17210 / Tourisme & Handicap reference")
    ] = None,
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
            en17210_ref=en17210,
        )
        return f"criterion edited: {criterion.slug}"

    _run_admin(callback)


@criterion_app.command("families")
def criterion_families(
    slug: Annotated[str, typer.Argument(help="Criterion slug")],
    family: Annotated[
        list[str] | None,
        typer.Option("--family", help="moteur, auditif, visuel, mental — repeatable"),
    ] = None,
) -> None:
    """Replace the handicap families a criterion belongs to."""

    async def callback(session: AsyncSession) -> str:
        criterion = await set_criterion_families(
            SqlAlchemyCriterionRepository(session), slug, family or []
        )
        return f"criterion families set: {criterion.slug} {criterion.handicap_families}"

    _run_admin(callback)


@families_app.command("sync")
def families_sync(
    file: Annotated[Path | None, typer.Option("--file", "-f", help="Reviewed families CSV")] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite families an operator edited by hand")
    ] = False,
) -> None:
    """Fill empty handicap families from data/referential/families.csv."""
    path = file or settings.data_dir / "families.csv"

    async def callback(session: AsyncSession) -> str:
        report = await apply_families(
            SqlAlchemyCriterionRepository(session),
            SqlAlchemyFilterRepository(session),
            load_families(path),
            overwrite=force,
        )
        return (
            f"families sync: criteria={report.criteria_updated} filters={report.filters_updated} "
            f"inherited={report.inherited} unchanged={report.unchanged}"
        )

    _run_admin(callback)


@families_app.command("audit")
def families_audit() -> None:
    """Fail when a criterion or filter carries no handicap family (DATA-01 gate)."""

    async def missing() -> list[str]:
        async with SessionLocal() as session:
            return await audit_families(
                SqlAlchemyCriterionRepository(session), SqlAlchemyFilterRepository(session)
            )

    slugs = asyncio.run(missing())
    if not slugs:
        typer.echo("families ok: every criterion and filter has at least one family")
        return
    typer.echo("missing families:")
    for slug in slugs:
        typer.echo(slug)
    raise typer.Exit(code=1)


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

    _run_admin(callback, bump=False)


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

    _run_admin(callback, bump=False)


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


@import_app.command("acceslibre")
def import_acceslibre_command(
    file: Annotated[Path, typer.Option("--file", "-f", help="Local Acceslibre CSV/JSON export")],
    aliases: Annotated[
        Path | None,
        typer.Option("--aliases", help="Activity → category CSV (default: data/referential)"),
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Report resolution and write nothing")
    ] = False,
) -> None:
    """Import a local Acceslibre export; idempotent by (source, source_id)."""
    alias_path = aliases or settings.data_dir / "acceslibre_categories.csv"
    alias_map = load_category_aliases(alias_path)

    async def callback(session: AsyncSession) -> str:
        # The iterator is the contract: a national export is never materialised as a list.
        report = await import_acceslibre(
            SqlAlchemyPlaceRepository(session),
            SqlAlchemyCategoryRepository(session),
            SqlAlchemyCategoryMappingRepository(session),
            SqlAlchemyPlaceAliasRepository(session),
            SqlAlchemyMergeLogRepository(session),
            iter_acceslibre_rows(file),
            aliases=alias_map,
            dry_run=dry_run,
        )
        lines = [
            f"acceslibre import: created={report.created} linked={report.linked} "
            f"review={report.review} skipped={report.skipped} resolved={report.resolved} "
            f"unresolved={len(report.unresolved)} dry_run={dry_run}"
        ]
        ranked = sorted(report.unresolved.items(), key=lambda item: (-item[1], item[0]))
        lines.extend(f"  unresolved: {value}={count}" for value, count in ranked[:20])
        return "\n".join(lines)

    _run_admin(callback, bump=False, commit=not dry_run)


@import_app.command("report")
def import_report(
    limit: Annotated[int, typer.Option("--limit", help="Max unresolved values listed")] = 50,
) -> None:
    """List places per source and every imported category that did not resolve (DATA-02 gate)."""

    async def collect() -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
        async with SessionLocal() as session:
            places = SqlAlchemyPlaceRepository(session)
            return await places.count_by_source(), await places.unresolved_categories()

    by_source, unresolved = asyncio.run(collect())
    for source, count in by_source:
        typer.echo(f"places by source: {source}={count}")
    if not by_source:
        typer.echo("places by source: none")
    for value, count in unresolved[:limit]:
        typer.echo(f"{value}={count}")
    total = sum(count for _, count in unresolved)
    typer.echo(f"unresolved total={total} across {len(unresolved)} source values")
    if total:
        raise typer.Exit(code=1)


@duplicates_app.command("list")
def duplicates_list(
    limit: Annotated[int, typer.Option("--limit", help="Max rows shown")] = 50,
) -> None:
    """List the duplicate candidates waiting for an operator decision (DATA-03)."""

    async def callback(session: AsyncSession) -> str:
        rows = await list_pending(SqlAlchemyPlaceRepository(session), limit)
        return "\n".join(
            f"{row.place_id}\t{row.score:.3f}\t{row.place_name} -> {row.candidate_name}"
            f"\t{row.place_city or ''}"
            f"{'' if in_review_band(row.score) else '  [out of band]'}"
            for row in rows
        )

    _run_admin(callback, bump=False)


@duplicates_app.command("merge")
def duplicates_merge(
    place_id: Annotated[int, typer.Argument(help="Place id from `duplicates list`")],
    note: Annotated[str | None, typer.Option("--note", help="Why they are the same place")] = None,
) -> None:
    """Soft-merge a place into its candidate: canonical link, alias, merge log, decision."""

    async def callback(session: AsyncSession) -> str:
        merged = await merge_duplicate(
            SqlAlchemyPlaceRepository(session),
            SqlAlchemyPlaceAliasRepository(session),
            SqlAlchemyMergeLogRepository(session),
            place_id,
            note=note,
        )
        return f"duplicate merged: {place_id} -> {merged.canonical_id}"

    _run_admin(callback)


@duplicates_app.command("reject")
def duplicates_reject(
    place_id: Annotated[int, typer.Argument(help="Place id from `duplicates list`")],
    note: Annotated[str | None, typer.Option("--note", help="Why they are distinct places")] = None,
) -> None:
    """Keep both places, record the rejection, and drop the pair from the queue."""

    async def callback(session: AsyncSession) -> str:
        await reject_duplicate(SqlAlchemyPlaceRepository(session), place_id, note=note)
        return f"duplicate rejected: {place_id} (both places kept)"

    _run_admin(callback)


@app.command("coverage")
def coverage_export(
    fmt: Annotated[
        Literal["table", "csv"], typer.Option("--format", help="table or csv")
    ] = "table",
    out: Annotated[Path | None, typer.Option("--out", help="Write the CSV to this file")] = None,
) -> None:
    """Export places, places with values and fill rate per category and country (DATA-04)."""

    async def callback(session: AsyncSession) -> str:
        rows = await coverage(SqlAlchemyCoverageRepository(session))
        if not rows:
            header = ",".join(COVERAGE_HEADER) if fmt == "csv" else "\t".join(COVERAGE_HEADER)
            return f"{header}\nno places yet"
        if fmt != "csv":
            return coverage_table(rows)
        payload = coverage_csv(rows)
        if out is None:
            return payload.rstrip("\n")
        out.write_text(payload, encoding="utf-8")
        return f"coverage csv: {len(rows) - 1} rows -> {out}"

    _run_admin(callback, bump=False)


def _run_api_key_admin(
    callback: Callable[[SqlAlchemyApiKeyRepository], Awaitable[str]],
) -> None:
    async def run() -> str:
        async with SessionLocal() as session:
            message = await callback(SqlAlchemyApiKeyRepository(session))
            await session.commit()
            return message

    try:
        message = asyncio.run(run())
    except DomainError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(message)


@api_key_app.command("create")
def api_key_create(
    label: Annotated[str, typer.Option("--label", "-l", help="Partner name")],
    rpm: Annotated[int, typer.Option("--rpm", help="Requests per minute")] = 60,
) -> None:
    """Create a key and print it once; only its hash is stored."""

    async def callback(keys: SqlAlchemyApiKeyRepository) -> str:
        raw, key = await create_api_key(keys, label, rpm)
        return (
            f"created api key #{key.id} ({key.label}, {key.rpm} rpm)\n{raw}\n"
            "Store it now: it is not shown again."
        )

    _run_api_key_admin(callback)


@api_key_app.command("list")
def api_key_list() -> None:
    """List keys without their secret."""

    async def callback(keys: SqlAlchemyApiKeyRepository) -> str:
        rows = await list_api_keys(keys)
        if not rows:
            return "no api keys"
        return "\n".join(
            f"#{row.id}\t{'active' if row.active else 'revoked'}\t{row.rpm} rpm\t{row.label}"
            for row in rows
        )

    _run_api_key_admin(callback)


@api_key_app.command("revoke")
def api_key_revoke(key_id: Annotated[int, typer.Argument(help="Key id")]) -> None:
    """Disable a key without deleting its audit trail."""

    async def callback(keys: SqlAlchemyApiKeyRepository) -> str:
        key = await revoke_api_key(keys, key_id)
        return f"revoked api key #{key.id} ({key.label})"

    _run_api_key_admin(callback)


@app.command("retention")
def retention(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Count without deleting")] = False,
) -> None:
    """Purge expired idempotency keys and refresh tokens (OPS-06)."""

    async def callback(session: AsyncSession) -> str:
        report = await run_retention(SqlAlchemyRetentionRepository(session), dry_run=dry_run)
        return (
            f"retention: idempotency={report.idempotency_deleted} "
            f"refresh={report.refresh_deleted} dry_run={report.dry_run}"
        )

    _run_admin(callback, bump=False)


if __name__ == "__main__":
    app()
