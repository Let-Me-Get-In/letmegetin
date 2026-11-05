"""keep the raw source category on every imported place

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("place", sa.Column("source_category", sa.String(length=120), nullable=True))
    op.create_index("ix_place_source_category", "place", ["source_category"])


def downgrade() -> None:
    op.drop_index("ix_place_source_category", table_name="place")
    op.drop_column("place", "source_category")
