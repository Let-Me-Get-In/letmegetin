"""Operator CLI: the only write path to the referential (no HTTP surface, no auth yet).

Usage: ``uv run python -m letmegetin.admin --help`` or ``uv run letmegetin-admin``.
"""

from __future__ import annotations

import asyncio
import csv
import os
import sys
from collections.abc import Awaitable, Callable, Iterable, Iterator
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

import typer
from sqlalchemy.ext.asyncio import AsyncSession

from letmegetin.application.accounts.api_keys import (
    create_api_key,
    list_api_keys,
    revoke_api_key,
)
from letmegetin.application.accounts.users import ensure_user
from letmegetin.application.places.category_resolution import load_category_aliases
from letmegetin.application.places.coverage import (
    COVERAGE_HEADER,
    coverage,
    coverage_csv,
    coverage_table,
)
from letmegetin.application.places.dedup_pass import recompute_duplicates
from letmegetin.application.places.duplicates import (
    in_review_band,
    list_pending,
    merge_batch,
    merge_duplicate,
    reject_duplicate,
)
from letmegetin.application.places.export import export_odbl, refuse_partner_window
from letmegetin.application.places.history import place_history
from letmegetin.application.places.import_acceslibre import (
    AcceslibreRow,
    import_acceslibre,
    iter_acceslibre_rows,
)
from letmegetin.application.places.import_osm import OsmRow, import_osm, render_unmatched
from letmegetin.application.places.lov2_export import load_identifier_rule
from letmegetin.application.places.push_acceslibre import PushReport, push_acceslibre
from letmegetin.application.places.reclassify import reclassify_places
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
from letmegetin.application.referential.licences import (
    audit_licences,
    format_matrix,
    load_licence_destinations,
    load_licences,
    load_source_licences,
    sync_licences,
)
from letmegetin.application.referential.osm_tags import audit_osm_tags, load_osm_accessibility_tags
from letmegetin.application.retention import run_retention
from letmegetin.config import settings
from letmegetin.core.db import SessionLocal
from letmegetin.core.exceptions import CategoryNotFound, DomainError
from letmegetin.domain.places.dedup import RELIABLE_MATCH_THRESHOLD
from letmegetin.domain.places.licence import DESTINATIONS
from letmegetin.domain.referential.entities import Category, Criterion, Label, VocabularyEntry
from letmegetin.domain.referential.labels import parse_label_pairs
from letmegetin.infrastructure.acceslibre.client import AccesLibreClient
from letmegetin.infrastructure.osm_pbf import iter_osm_rows
from letmegetin.infrastructure.persistence.export_repositories import (
    SqlAlchemyExportEventRepository,
    SqlAlchemyExportRepository,
)
from letmegetin.infrastructure.persistence.licence_repositories import SqlAlchemyLicenceRepository
from letmegetin.infrastructure.persistence.push_repositories import SqlAlchemyPushRepository
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
    SqlAlchemyUserRepository,
    SqlAlchemyVocabularyRepository,
)

app = typer.Typer(help="Curate the accessibility referential.")
category_app = typer.Typer(help="Add, edit and list place categories.")
criterion_app = typer.Typer(help="Add, edit and list criteria and options.")
vocabulary_app = typer.Typer(help="Import, list and promote the flat criteria vocabulary.")
labels_app = typer.Typer(help="Set multilingual labels on any referential entity.")
families_app = typer.Typer(help="Fill and audit handicap families (moteur, auditif, visuel…).")
licences_app = typer.Typer(help="Sync, render and audit the licence catalogue and matrix.")
import_app = typer.Typer(help="Import open place datasets (Acceslibre first).")
duplicates_app = typer.Typer(help="Review, merge or reject duplicate candidates from the import.")
place_app = typer.Typer(help="Read a place's change journal.")
export_app = typer.Typer(help="Write the open ODbL export (snapshot, delta or catch-up).")
api_key_app = typer.Typer(help="Create, list and revoke partner API keys.")
user_app = typer.Typer(help="Create and verify operator/E2E accounts.")
acceslibre_app = typer.Typer(help="Probe the AccesLibre ERP identifier and push owned answers.")
osm_app = typer.Typer(help="Audit the reviewed OSM tags and generate OSM changesets.")
app.add_typer(category_app, name="category")
app.add_typer(criterion_app, name="criterion")
app.add_typer(vocabulary_app, name="vocabulary")
app.add_typer(labels_app, name="labels")
app.add_typer(families_app, name="families")
app.add_typer(licences_app, name="licences")
app.add_typer(import_app, name="import")
app.add_typer(duplicates_app, name="duplicates")
app.add_typer(place_app, name="place")
app.add_typer(export_app, name="export")
app.add_typer(api_key_app, name="api-key")
app.add_typer(user_app, name="user")
app.add_typer(acceslibre_app, name="acceslibre")
app.add_typer(osm_app, name="osm")

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


@licences_app.command("sync")
def licences_sync(
    licences_file: Annotated[
        Path | None, typer.Option("--licences", help="Reviewed licence catalogue CSV")
    ] = None,
    destinations_file: Annotated[
        Path | None, typer.Option("--destinations", help="Reviewed destination matrix CSV")
    ] = None,
    sources_file: Annotated[
        Path | None, typer.Option("--sources", help="Reviewed source → licence CSV")
    ] = None,
) -> None:
    """Load the three reviewed licence CSVs; a change bumps the referential version (D-08)."""
    licences_path = licences_file or settings.data_dir / "licences.csv"
    destinations_path = destinations_file or settings.data_dir / "licence_destinations.csv"
    sources_path = sources_file or settings.data_dir / "source_licences.csv"

    async def callback(session: AsyncSession) -> str:
        licences = load_licences(licences_path)
        slugs = {licence.slug for licence in licences}
        report = await sync_licences(
            SqlAlchemyLicenceRepository(session),
            licences,
            load_licence_destinations(destinations_path, slugs),
            load_source_licences(sources_path, slugs),
        )
        return (
            f"licences sync: created={report.created} updated={report.updated} "
            f"unchanged={report.unchanged}"
        )

    _run_admin(callback)


@licences_app.command("matrix")
def licences_matrix() -> None:
    """Print the redistribution matrix, grouped by destination."""

    async def callback(session: AsyncSession) -> str:
        return format_matrix(await SqlAlchemyLicenceRepository(session).list_destinations())

    _run_admin(callback, bump=False)


@licences_app.command("excluded")
def licences_excluded(
    destination: Annotated[
        str, typer.Option("--destination", help="open_export, osm or lov2_partner")
    ],
    verbose: Annotated[
        bool, typer.Option("--verbose", help="List every excluded place id and its licence")
    ] = False,
) -> None:
    """Count, per source and licence, what the matrix keeps out of a destination (D-14)."""
    if destination not in DESTINATIONS:
        allowed = ", ".join(DESTINATIONS)
        typer.echo(f"unknown destination '{destination}' (allowed: {allowed})", err=True)
        raise typer.Exit(code=1)

    async def callback(session: AsyncSession) -> str:
        repository = SqlAlchemyLicenceRepository(session)
        counts = await repository.exclusion_counts(destination)
        if not counts:
            return f"{destination}: nothing excluded"
        total = sum(count for _, _, count in counts)
        lines = [
            f"{destination}: excluded={total} across {len(counts)} source/licence groups",
            *(
                f"  {source}\t{licence or '(no licence)'}\t{count}"
                for source, licence, count in counts
            ),
        ]
        if verbose:
            lines.extend(
                f"  place {place_id}\t{licence or '(no licence)'}"
                for place_id, licence in await repository.excluded_ids(destination)
            )
        return "\n".join(lines)

    _run_admin(callback, bump=False)


@licences_app.command("audit")
def licences_audit() -> None:
    """Fail when the catalogue or the matrix has a gap (D-08 gate)."""

    async def issues() -> list[str]:
        async with SessionLocal() as session:
            return await audit_licences(SqlAlchemyLicenceRepository(session))

    found = asyncio.run(issues())
    if not found:
        typer.echo("licences ok: every licence has a full matrix and every row resolves")
        return
    typer.echo("licence audit:")
    for issue in found:
        typer.echo(issue)
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
    no_dedup: Annotated[
        bool,
        typer.Option(
            "--no-dedup",
            help="Skip the per-row duplicate lookup (first bulk load; run the dedup pass after)",
        ),
    ] = False,
) -> None:
    """Import a local Acceslibre export; idempotent by (source, source_id)."""
    alias_path = aliases or settings.data_dir / "acceslibre_categories.csv"
    alias_map = load_category_aliases(alias_path)

    def _progress(rows: Iterable[AcceslibreRow], every: int = 5000) -> Iterator[AcceslibreRow]:
        # One transaction means the table shows nothing until the end: this is the
        # only way to tell "slow" apart from "stuck" while a national load runs.
        for index, row in enumerate(rows, 1):
            if index % every == 0:
                print(f"  ... {index} lignes lues", file=sys.stderr, flush=True)
            yield row

    async def callback(session: AsyncSession) -> str:
        # The iterator is the contract: a national export is never materialised as a list.
        report = await import_acceslibre(
            SqlAlchemyPlaceRepository(session),
            SqlAlchemyCategoryRepository(session),
            SqlAlchemyCategoryMappingRepository(session),
            SqlAlchemyPlaceAliasRepository(session),
            SqlAlchemyMergeLogRepository(session),
            _progress(iter_acceslibre_rows(file)),
            aliases=alias_map,
            dry_run=dry_run,
            dedup=not no_dedup,
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


@import_app.command("osm")
def import_osm_command(
    file: Annotated[Path, typer.Option("--file", "-f", help="Local .osm.pbf extract")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Report resolution and write nothing")
    ] = False,
    no_dedup: Annotated[
        bool,
        typer.Option(
            "--no-dedup",
            help="Skip the per-row duplicate lookup (first bulk load; run the dedup pass after)",
        ),
    ] = False,
) -> None:
    """Import a local OpenStreetMap PBF extract; idempotent by (source, source_id)."""

    def _progress(rows: Iterable[OsmRow], every: int = 5000) -> Iterator[OsmRow]:
        # One transaction means the table shows nothing until the end: this is the
        # only way to tell "slow" apart from "stuck" while a national extract runs.
        for index, row in enumerate(rows, 1):
            if index % every == 0:
                print(f"  ... {index} objects read", file=sys.stderr, flush=True)
            yield row

    async def callback(session: AsyncSession) -> str:
        report = await import_osm(
            SqlAlchemyPlaceRepository(session),
            SqlAlchemyCategoryRepository(session),
            SqlAlchemyCategoryMappingRepository(session),
            SqlAlchemyPlaceAliasRepository(session),
            SqlAlchemyMergeLogRepository(session),
            SqlAlchemyCriterionRepository(session),
            _progress(iter_osm_rows(file)),
            dry_run=dry_run,
            dedup=not no_dedup,
        )
        lines = [
            f"osm import: created={report.created} linked={report.linked} "
            f"review={report.review} skipped={report.skipped} resolved={report.resolved} "
            f"unresolved={report.unresolved} dry_run={dry_run}"
        ]
        lines.extend(render_unmatched(report))
        return "\n".join(lines)

    _run_admin(callback, bump=False, commit=not dry_run)


@osm_app.command("audit")
def osm_audit() -> None:
    """Fail when a reviewed OSM tag or accessibility value names nothing (T-16-03)."""

    async def gaps() -> list[str]:
        async with SessionLocal() as session:
            return audit_osm_tags(
                await SqlAlchemyCategoryRepository(session).list_all(),
                await SqlAlchemyCriterionRepository(session).list_all(),
                await SqlAlchemyCategoryMappingRepository(session).list_osm_tags(),
                load_osm_accessibility_tags(settings.data_dir / "osm_accessibility_tags.csv"),
            )

    try:
        found = asyncio.run(gaps())
    except DomainError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    if not found:
        typer.echo("osm tags ok: every osm_tag and accessibility value resolves")
        return
    typer.echo("osm tag gaps:")
    for gap in found:
        typer.echo(gap)
    raise typer.Exit(code=1)


@import_app.command("reclassify")
def import_reclassify(
    aliases: Annotated[
        Path | None,
        typer.Option("--aliases", help="Activity → category CSV (default: data/referential)"),
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Report resolution and write nothing")
    ] = False,
) -> None:
    """Re-apply the alias file to places an earlier import left without a category."""
    alias_path = aliases or settings.data_dir / "acceslibre_categories.csv"
    alias_map = load_category_aliases(alias_path)

    async def callback(session: AsyncSession) -> str:
        report = await reclassify_places(
            SqlAlchemyPlaceRepository(session),
            SqlAlchemyCategoryRepository(session),
            SqlAlchemyCategoryMappingRepository(session),
            alias_map,
            dry_run=dry_run,
        )
        lines = [
            f"reclassify: values={len(report.resolved)} "
            f"places={sum(report.resolved.values())} "
            f"unresolved={len(report.unresolved)} dry_run={dry_run}"
        ]
        lines.extend(
            f"  still unresolved: {value}={count}" for value, count in report.unresolved[:20]
        )
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
    show_all: Annotated[
        bool, typer.Option("--all", help="Also show pairs below the reliable score")
    ] = False,
) -> None:
    """List the duplicate candidates waiting for an operator decision (DATA-03)."""

    async def callback(session: AsyncSession) -> str:
        repo = SqlAlchemyPlaceRepository(session)
        rows = await list_pending(repo, limit, None if show_all else RELIABLE_MATCH_THRESHOLD)
        # Probe the unfiltered queue so a blank listing never looks like an empty one.
        hidden = [] if show_all else await list_pending(repo, 1, None)
        if not rows and not hidden:
            return ""
        lines = [
            f"{row.place_id}\t{row.score:.3f}\t{row.place_name} -> {row.candidate_name}"
            f"\t{row.place_city or ''}"
            f"{'' if in_review_band(row.score) else '  [out of band]'}"
            for row in rows
        ]
        if hidden:
            lines.append(
                f"(scores below {RELIABLE_MATCH_THRESHOLD:.2f} hidden; use --all to see them)"
            )
        return "\n".join(lines)

    _run_admin(callback, bump=False)


@duplicates_app.command("recompute")
def duplicates_recompute(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Count without writing")] = False,
    radius: Annotated[float, typer.Option("--radius", help="Search radius in metres")] = 50.0,
) -> None:
    """Fill the review queue in one pass over the whole table (the import leaves it empty)."""

    async def callback(session: AsyncSession) -> str:
        report = await recompute_duplicates(
            SqlAlchemyPlaceRepository(session), radius_m=radius, dry_run=dry_run
        )
        return (
            f"duplicates recompute: places={report.places} pairs={report.pairs} "
            f"cleared={report.cleared} flagged={report.flagged} dry_run={report.dry_run}"
        )

    _run_admin(callback, bump=False, commit=not dry_run)


@duplicates_app.command("merge-batch")
def duplicates_merge_batch(
    min_score: Annotated[
        float, typer.Option("--min-score", help="Merge every pair at or above this score")
    ] = 1.0,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Count without writing")] = False,
    note: Annotated[str | None, typer.Option("--note", help="Note on every decision")] = None,
) -> None:
    """Merge a whole score band in one pass. Always start with --dry-run."""

    async def callback(session: AsyncSession) -> str:
        report = await merge_batch(
            SqlAlchemyPlaceRepository(session),
            SqlAlchemyPlaceAliasRepository(session),
            SqlAlchemyMergeLogRepository(session),
            min_score=min_score,
            note=note,
            dry_run=dry_run,
        )
        return (
            f"duplicates merge-batch: candidates={report.candidates} merged={report.merged} "
            f"skipped={report.skipped} dry_run={report.dry_run}"
        )

    _run_admin(callback, bump=False, commit=not dry_run)


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


@place_app.command("history")
def place_history_command(
    slug: Annotated[str, typer.Argument(help="Place slug")],
) -> None:
    """Print date, op, actor and the changed fields of every journal event (D-13)."""

    async def callback(session: AsyncSession) -> str:
        lines = await place_history(SqlAlchemyExportEventRepository(session), slug)
        return "\n".join(lines)

    _run_admin(callback, bump=False)


def _parse_since(value: str | None) -> tuple[int | None, date | None]:
    """``--since`` takes a journal sequence number or an ISO date, never both (D-10)."""
    if value is None:
        return None, None
    try:
        return int(value), None
    except ValueError:
        pass
    try:
        return None, date.fromisoformat(value)
    except ValueError as exc:
        raise DomainError(
            f"--since needs a journal sequence number or an ISO date, got '{value}'"
        ) from exc


@export_app.command("odbl")
def export_odbl_command(
    out: Annotated[Path, typer.Option("--out", help="Directory the ZIPs and latest.json go to")],
    delta: Annotated[
        bool, typer.Option("--delta", help="Publish only the events since the watermark")
    ] = False,
    since: Annotated[
        str | None, typer.Option("--since", help="Cumulative catch-up from a seq or an ISO date")
    ] = None,
    destination: Annotated[
        str,
        typer.Option("--destination", help="open_export or lov2_partner (full snapshots only)"),
    ] = "open_export",
) -> None:
    """Write the ODbL ZIP and latest.json; a snapshot also prunes the journal (D-11, D-15)."""

    async def callback(session: AsyncSession) -> str:
        since_seq, since_date = _parse_since(since)
        refuse_partner_window(destination, delta=delta, since=since_seq, since_date=since_date)
        # A partner archive in the public directory would publish withheld rows and
        # overwrite the ODbL latest.json the API serves (T-15-01).
        if destination != "open_export" and out.resolve() == settings.export_dir.resolve():
            raise DomainError(
                f"--out points at the served export directory: a {destination} archive must "
                "not be published there"
            )
        repository = SqlAlchemyExportRepository(session)
        events = SqlAlchemyExportEventRepository(session)
        if destination == "lov2_partner":
            # The partner feed projects every row into AccesLibre's vocabulary (D-04, D-05).
            from letmegetin.application.places.lov2_export import build_lov2_feed

            report = await build_lov2_feed(repository, events, out=out)
        else:
            report = await export_odbl(
                repository,
                events,
                out=out,
                since=since_seq,
                since_date=since_date,
                delta=delta,
                destination=destination,
            )
        lines = [
            f"{report.mode} export: {report.name}",
            "  files: " + ", ".join(f"{name}={count}" for name, count in report.files.items()),
            f"  snapshot={report.snapshot_seq} watermark={report.watermark} "
            f"floor={report.retention_floor_seq}",
        ]
        if destination == "lov2_partner":
            lines.append(f"  mapping: {out / 'mapping.csv'}")
        for label, counts in (
            ("excluded places", report.excluded_places),
            ("excluded answers", report.excluded_answers),
            ("place-withheld answers", report.place_withheld_answers),
        ):
            lines.extend(
                f"  {label}: {source} {licence or '(no licence)'} {count}"
                for source, licence, count in counts
            )
        if report.pruned_events or report.pruned_deltas:
            lines.append(
                f"  pruned: events={report.pruned_events} deltas={len(report.pruned_deltas)}"
            )
        return "\n".join(lines)

    _run_admin(callback, bump=False)


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


def _run_user_admin(
    callback: Callable[[SqlAlchemyUserRepository], Awaitable[str]],
) -> None:
    """Commit-only runner: accounts do not touch the referential, so no grid rebuild."""

    async def run() -> str:
        async with SessionLocal() as session:
            message = await callback(SqlAlchemyUserRepository(session))
            await session.commit()
            return message

    try:
        message = asyncio.run(run())
    except DomainError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(message)


def _read_user_password() -> str:
    """Read the password from the environment or a masked prompt, never from argv."""

    password = os.environ.get("LETMEGETIN_USER_PASSWORD") or ""
    if not password:
        password = typer.prompt("Password", hide_input=True, default="")
    if not password:
        typer.echo(
            "error: set LETMEGETIN_USER_PASSWORD or type the password at the prompt", err=True
        )
        raise typer.Exit(code=1)
    return password


@user_app.command("ensure")
def user_ensure(
    email: Annotated[str, typer.Argument(help="Account email")],
    display_name: Annotated[
        str | None, typer.Option("--display-name", help="Public display name")
    ] = None,
    verified: Annotated[
        bool, typer.Option("--verified/--no-verified", help="Mark the email verified now")
    ] = False,
) -> None:
    """Create an account if missing, or check the existing one, and report the outcome.

    The password is never an option: it comes from LETMEGETIN_USER_PASSWORD or a
    hidden prompt, so it stays out of `ps` output and shell history.
    """
    password = _read_user_password()

    async def callback(users: SqlAlchemyUserRepository) -> str:
        outcome = await ensure_user(users, email, password, display_name, verified)
        return f"user {email}: {outcome}"

    _run_user_admin(callback)


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


_IDENTIFIER_RULE_FILE = "acceslibre_identifier_rule.csv"


def _write_identifier_rule(path: Path, rule: str, detail: str) -> None:
    """Overwrite the single recorded rule that the feed and the push read (D-05)."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["rule", "detail"])
        writer.writerow([rule, detail])


def probe_identifier(client: AccesLibreClient, source_id: str, path: Path) -> str:
    """Read-only probe: settle Open Question 1 and record the rule the feed will key on.

    Both documented lookups are tried, then one ``get_erp`` prints the read ``accessibilite``
    section names (A2). A rule is written only after every call succeeded, so a refusal leaves
    the previous rule in place. A read cannot confirm A1 (the PATCH success shape).
    """
    by_uuid = client.list_erps(uuid=source_id)
    by_source = client.list_erps(source="acceslibre", source_id=source_id)
    lines = [
        f"?uuid={source_id} -> {len(by_uuid)} erp(s)",
        f"?source=acceslibre&source_id={source_id} -> {len(by_source)} erp(s)",
    ]
    slugs: list[str] = []
    for erp in [*by_source, *by_uuid]:
        slug = erp.get("slug")
        lines.append(f"  slug={slug} source={erp.get('source')} source_id={erp.get('source_id')}")
        if isinstance(slug, str) and slug and slug not in slugs:
            slugs.append(slug)

    if not slugs:
        rule = "blocked"
        detail = (
            f"neither ?uuid= nor ?source=acceslibre&source_id= returned an ERP for '{source_id}'"
        )
    elif source_id in slugs:
        rule = "origin_id"
        detail = "the ERP slug is the origin_id itself, so keying on origin_id addresses it"
    else:
        rule = "slug"
        detail = (
            f"the ERP slug '{slugs[0]}' differs from origin_id '{source_id}' — "
            "re-import the slug column to populate erp_slug"
        )

    if slugs:
        body = client.get_erp(slugs[0])
        section = body.get("accessibilite")
        keys = sorted(section) if isinstance(section, dict) else []
        lines.append(f"accessibilite keys ({slugs[0]}): {', '.join(keys)}")

    _write_identifier_rule(path, rule, detail)
    lines.append(f"rule recorded in {path}: {rule}")
    return "\n".join(lines)


@acceslibre_app.command("probe")
def acceslibre_probe(
    source_id: Annotated[str, typer.Argument(help="Our place.source_id (AccesLibre's CSV id)")],
) -> None:
    """Resolve which identifier AccesLibre addresses an ERP by (D-05, Open Question 1)."""
    key = settings.acceslibre_api_key
    if not key:
        typer.echo(
            "error: LETMEGETIN_ACCESLIBRE_API_KEY is not set; the probe never calls "
            "AccesLibre unauthenticated",
            err=True,
        )
        raise typer.Exit(code=1)
    client = AccesLibreClient(key)
    path = settings.data_dir / _IDENTIFIER_RULE_FILE

    async def callback(_session: AsyncSession) -> str:
        try:
            return probe_identifier(client, source_id, path)
        finally:
            client.close()

    _run_admin(callback, bump=False, commit=False)


def _push_summary(report: PushReport) -> str:
    """One line of counters, then the per-ERP diff a dry run printed (D-14)."""
    reasons = (
        ", ".join(f"{reason}={count}" for reason, count in sorted(report.skipped_reasons.items()))
        or "none"
    )
    lines = [
        f"acceslibre push: pushed={report.pushed} skipped={report.skipped} "
        f"reasons={reasons} dry_run={report.dry_run}"
    ]
    lines.extend(
        f"  {identifier}: "
        + ", ".join(f"{field}={value}" for field, value in sorted(fields.items()))
        for identifier, fields in sorted(report.diffs.items())
    )
    if report.dry_run:
        lines.append("  dry run: nothing was patched and no journal row was written")
    return "\n".join(lines)


@acceslibre_app.command("push")
def acceslibre_push(
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print the diff per place and write nothing")
    ] = False,
) -> None:
    """Push the answers we own: read each ERP, diff, patch only what differs (D-10, D-14)."""

    async def callback(session: AsyncSession) -> str:
        key = settings.acceslibre_api_key
        if key is None:
            raise DomainError(
                "no AccesLibre API key: set LETMEGETIN_ACCESLIBRE_API_KEY (see 15-PARTNER-ASK.md)"
            )
        rule = load_identifier_rule(settings.data_dir / _IDENTIFIER_RULE_FILE)
        client = AccesLibreClient(key)
        try:
            report = await push_acceslibre(
                SqlAlchemyPushRepository(session), client, rule=rule, dry_run=dry_run
            )
        finally:
            client.close()
        return _push_summary(report)

    _run_admin(callback, bump=False, commit=not dry_run)


if __name__ == "__main__":
    app()
