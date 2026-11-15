"""append-only journal of outbound AccesLibre pushes (D-12)

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "acceslibre_push_write",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "place_id",
            sa.Integer(),
            sa.ForeignKey("place.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "criterion_id",
            sa.Integer(),
            sa.ForeignKey("criteria.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("source_license", sa.String(64), nullable=True),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(32), nullable=True),
        sa.Column("actor", sa.String(64), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "decision IN ('accepted','skipped')", name="acceslibre_push_write_decision_ck"
        ),
        sa.CheckConstraint(
            "reason IS NULL OR reason IN "
            "('their_fresher','rpa_locked','not_redistributable','unmappable','invalid_value')",
            name="acceslibre_push_write_reason_ck",
        ),
    )
    op.create_index("ix_acceslibre_push_write_place_id", "acceslibre_push_write", ["place_id"])


def downgrade() -> None:
    op.drop_index("ix_acceslibre_push_write_place_id", table_name="acceslibre_push_write")
    op.drop_table("acceslibre_push_write")
