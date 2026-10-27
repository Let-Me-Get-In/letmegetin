"""reviews and source photos for place records

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("author_name", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="published"),
        sa.Column("created", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="review_rating_range"),
        sa.ForeignKeyConstraint(["place_id"], ["place.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_place_id", "review", ["place_id"], unique=False)
    op.create_index("ix_review_place_created", "review", ["place_id", "created"], unique=False)

    op.create_table(
        "place_photo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("credit", sa.String(length=255), nullable=True),
        sa.Column("license", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["place_id"], ["place.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("place_id", "url", name="place_photo_url_uc"),
    )
    op.create_index("ix_place_photo_place_id", "place_photo", ["place_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_place_photo_place_id", table_name="place_photo")
    op.drop_table("place_photo")
    op.drop_index("ix_review_place_created", table_name="review")
    op.drop_index("ix_review_place_id", table_name="review")
    op.drop_table("review")
