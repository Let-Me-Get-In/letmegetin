"""referential curation: vocabulary table and mapping flags

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "criterion_vocabulary",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("label", _JSONB, nullable=False),
        sa.Column("description", _JSONB, nullable=False),
        sa.Column("promoted_criterion_id", sa.Integer(), nullable=True),
        sa.Column("created", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["promoted_criterion_id"], ["criteria.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_criterion_vocabulary_slug", "criterion_vocabulary", ["slug"], unique=True)

    op.add_column(
        "criteria",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    # A Phase 1 database already holds the category-1 grid: reuse it as the default set.
    op.execute(
        "UPDATE criteria SET is_default = true "
        "WHERE parent_id IS NOT NULL "
        "AND parent_id IN (SELECT id FROM criteria WHERE parent_id IS NULL)"
    )

    op.add_column(
        "category_criteria",
        sa.Column("excluded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("category_criteria", "excluded")
    op.drop_column("criteria", "is_default")
    op.drop_index("ix_criterion_vocabulary_slug", table_name="criterion_vocabulary")
    op.drop_table("criterion_vocabulary")
