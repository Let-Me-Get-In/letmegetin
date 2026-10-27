"""initial referential schema

Revision ID: 0001
Revises:
Create Date: 2026-10-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSONB = postgresql.JSONB(astext_type=sa.Text())


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("label", _JSONB, nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_categories_parent_id", "categories", ["parent_id"], unique=False)
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)

    op.create_table(
        "criteria",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("need_children", sa.Boolean(), nullable=False),
        sa.Column("label", _JSONB, nullable=False),
        sa.Column("description", _JSONB, nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["parent_id"], ["criteria.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_criteria_parent_id", "criteria", ["parent_id"], unique=False)
    op.create_index("ix_criteria_slug", "criteria", ["slug"], unique=True)

    op.create_table(
        "accessibility_filters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("label", _JSONB, nullable=False),
        sa.Column("criterion_id", sa.Integer(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["criterion_id"], ["criteria.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accessibility_filters_slug", "accessibility_filters", ["slug"], unique=True)

    op.create_table(
        "other_information",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("label", _JSONB, nullable=False),
        sa.Column("link", sa.String(length=500), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["parent_id"], ["other_information.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="other_information_name_uc"),
    )
    op.create_index("ix_other_information_slug", "other_information", ["slug"], unique=True)

    op.create_table(
        "category_criteria",
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("criterion_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["criterion_id"], ["criteria.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("category_id", "criterion_id"),
    )


def downgrade() -> None:
    op.drop_table("category_criteria")
    op.drop_index("ix_other_information_slug", table_name="other_information")
    op.drop_table("other_information")
    op.drop_index("ix_accessibility_filters_slug", table_name="accessibility_filters")
    op.drop_table("accessibility_filters")
    op.drop_index("ix_criteria_parent_id", table_name="criteria")
    op.drop_index("ix_criteria_slug", table_name="criteria")
    op.drop_table("criteria")
    op.drop_index("ix_categories_parent_id", table_name="categories")
    op.drop_index("ix_categories_slug", table_name="categories")
    op.drop_table("categories")
