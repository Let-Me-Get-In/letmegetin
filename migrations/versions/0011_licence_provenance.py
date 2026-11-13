"""record licence provenance on places and answers, and backfill every row

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-13
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSONB = postgresql.JSONB(astext_type=sa.Text())

# The reviewed source → licence correspondence the backfill resolves against (LIC-05).
_SOURCE_LICENCES = Path(__file__).resolve().parents[2] / "data/referential/source_licences.csv"

# place holds ~634k rows: update in batches, never as one full-table rewrite (T-12-01).
_BATCH = 10_000

_PLACE_BATCH = sa.text(
    "UPDATE place SET source_license = :licence WHERE id IN ("
    "SELECT id FROM place WHERE source = :source AND source_license IS NULL LIMIT :batch)"
)
# place_accessibility has a composite primary key, so ctid is the row locator for the batch.
_ANSWER_BATCH = sa.text(
    "UPDATE place_accessibility SET source_license = :licence WHERE ctid IN ("
    "SELECT ctid FROM place_accessibility "
    "WHERE source = :source AND source_license IS NULL LIMIT :batch)"
)
_PLACE_GAPS = sa.text(
    "SELECT source, count(*) FROM place WHERE source_license IS NULL GROUP BY source"
)
_ANSWER_GAPS = sa.text(
    "SELECT source, count(*) FROM place_accessibility WHERE source_license IS NULL GROUP BY source"
)


def _reviewed_mapping() -> dict[str, str]:
    """Read ``source;licence_slug`` rows; never a hard-coded CASE (LIC-05, D-07)."""
    with _SOURCE_LICENCES.open(encoding="utf-8", newline="") as handle:
        return {
            row["source"].strip(): row["licence_slug"].strip()
            for row in csv.DictReader(handle, delimiter=";")
            if (row.get("source") or "").strip() and (row.get("licence_slug") or "").strip()
        }


def _batched_licence_update(
    bind: sa.Connection, statement: sa.TextClause, source: str, licence: str
) -> None:
    """Set ``source_license`` on every row owned by ``source``, one batch at a time."""
    while True:
        result = bind.execute(statement, {"licence": licence, "source": source, "batch": _BATCH})
        if result.rowcount == 0:
            return


def _backfill(bind: sa.Connection) -> None:
    """Fill the provenance of every pre-existing row from data already present (D-04)."""
    # The answer's source is already in the value JSONB written by contribute/import.
    bind.execute(
        sa.text("UPDATE place_accessibility SET source = value->>'source' WHERE source IS NULL")
    )
    # Attribution follows the same data: importer:<source>, or user:<id> when known.
    bind.execute(
        sa.text(
            "UPDATE place_accessibility SET actor = CASE WHEN source = 'user' "
            "THEN 'user:' || coalesce(value->>'user_id', 'unknown') "
            "ELSE 'importer:' || source END "
            "WHERE actor IS NULL"
        )
    )

    for source, licence in _reviewed_mapping().items():
        _batched_licence_update(bind, _PLACE_BATCH, source, licence)
        _batched_licence_update(bind, _ANSWER_BATCH, source, licence)

    unowned = bind.execute(
        sa.text("SELECT count(*) FROM place_accessibility WHERE source IS NULL OR source = ''")
    ).scalar_one()
    if unowned:
        raise RuntimeError(
            f"licence backfill: {unowned} place_accessibility rows carry no source in their "
            "value JSONB — add the source to source_licences.csv review, never a silent NULL"
        )

    gaps: list[str] = []
    for table, statement in (
        ("place", _PLACE_GAPS),
        ("place_accessibility", _ANSWER_GAPS),
    ):
        gaps.extend(f"{table}.{source}={count}" for source, count in bind.execute(statement).all())
    if gaps:
        raise RuntimeError(
            "licence backfill left rows without a licence: "
            + ", ".join(gaps)
            + " — every source needs a reviewed row in source_licences.csv"
        )


def _create_licence_tables() -> None:
    op.create_table(
        "licence",
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("obligations", _JSONB, nullable=False),
        sa.PrimaryKeyConstraint("slug"),
    )
    op.create_table(
        "licence_destination",
        sa.Column("licence_slug", sa.String(length=64), nullable=False),
        sa.Column("destination", sa.String(length=32), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["licence_slug"], ["licence.slug"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "destination IN ('open_export','osm','lov2_partner')",
            name="licence_destination_destination_ck",
        ),
        sa.PrimaryKeyConstraint("licence_slug", "destination"),
    )
    op.create_table(
        "source_licence",
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("licence_slug", sa.String(length=64), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["licence_slug"], ["licence.slug"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("source"),
    )
    op.create_table(
        "place_accessibility_write",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("criterion_id", sa.Integer(), nullable=False),
        sa.Column("value", _JSONB, nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_license", sa.String(length=64), nullable=True),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=True),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("created", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["place_id"], ["place.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["criterion_id"], ["criteria.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "decision IN ('accepted','rejected')",
            name="place_accessibility_write_decision_ck",
        ),
        sa.CheckConstraint(
            "reason IS NULL OR reason IN ('stale','other_source','not_redistributable')",
            name="place_accessibility_write_reason_ck",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_place_accessibility_write_place_id",
        "place_accessibility_write",
        ["place_id"],
        unique=False,
    )


def upgrade() -> None:
    op.add_column("place", sa.Column("source_license", sa.String(length=64), nullable=True))
    op.add_column("place", sa.Column("source_url", sa.String(length=1000), nullable=True))
    op.add_column("place", sa.Column("retrieved_at", sa.DateTime(), nullable=True))
    op.add_column("place", sa.Column("observed_at", sa.DateTime(), nullable=True))

    # Nullable first: the backfill fills both from the existing value JSONB.
    op.add_column("place_accessibility", sa.Column("source", sa.String(length=32), nullable=True))
    op.add_column(
        "place_accessibility", sa.Column("source_license", sa.String(length=64), nullable=True)
    )
    op.add_column("place_accessibility", sa.Column("observed_at", sa.DateTime(), nullable=True))
    op.add_column(
        "place_accessibility",
        sa.Column("recorded_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column("place_accessibility", sa.Column("actor", sa.String(length=64), nullable=True))

    _create_licence_tables()
    _backfill(op.get_bind())

    # Only once the backfill proves every row resolved (D-04, D-15).
    op.alter_column("place_accessibility", "source", nullable=False)
    op.alter_column("place_accessibility", "actor", nullable=False)


def downgrade() -> None:
    op.drop_index("ix_place_accessibility_write_place_id", table_name="place_accessibility_write")
    op.drop_table("place_accessibility_write")
    op.drop_table("source_licence")
    op.drop_table("licence_destination")
    op.drop_table("licence")
    for column in ("actor", "recorded_at", "observed_at", "source_license", "source"):
        op.drop_column("place_accessibility", column)
    for column in ("observed_at", "retrieved_at", "source_url", "source_license"):
        op.drop_column("place", column)
