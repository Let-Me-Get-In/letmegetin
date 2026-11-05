"""persist duplicate candidates and the operator review decisions

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("place", sa.Column("duplicate_of_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "place_duplicate_of_id_fkey",
        "place",
        "place",
        ["duplicate_of_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_place_duplicate_of_id", "place", ["duplicate_of_id"], unique=False)

    op.create_table(
        "place_review_decision",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=True),
        sa.Column("score", sa.Double(), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("actor", sa.String(length=32), server_default="operator", nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["place_id"], ["place.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["place.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "decision IN ('merge','reject')", name="place_review_decision_decision_ck"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_place_review_decision_place_id", "place_review_decision", ["place_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_place_review_decision_place_id", table_name="place_review_decision")
    op.drop_table("place_review_decision")
    op.drop_index("ix_place_duplicate_of_id", table_name="place")
    op.drop_constraint("place_duplicate_of_id_fkey", "place", type_="foreignkey")
    op.drop_column("place", "duplicate_of_id")
