"""accounts, contribution log and review authorship

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="user"),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("created", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "contribution",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("criterion_id", sa.Integer(), nullable=False),
        sa.Column("value", _JSONB, nullable=False),
        sa.Column("created", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["place_id"], ["place.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["criterion_id"], ["criteria.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contribution_user_id", "contribution", ["user_id"], unique=False)
    op.create_index("ix_contribution_place_id", "contribution", ["place_id"], unique=False)

    op.add_column("review", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "review_user_id_fkey", "review", "users", ["user_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_review_user_id", "review", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_review_user_id", table_name="review")
    op.drop_constraint("review_user_id_fkey", "review", type_="foreignkey")
    op.drop_column("review", "user_id")
    op.drop_index("ix_contribution_place_id", table_name="contribution")
    op.drop_index("ix_contribution_user_id", table_name="contribution")
    op.drop_table("contribution")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
