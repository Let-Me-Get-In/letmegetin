"""OSM object identity on place: the object version and its raw tag set (D-03 amendment)

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # An .osmChange <modify> replaces the object wholesale: the publisher needs the version
    # to address it and the full raw tag set to re-emit it without deleting live tags.
    # Both stay NULL for every non-OSM row and are never backfilled.
    op.add_column("place", sa.Column("osm_version", sa.Integer(), nullable=True))
    op.add_column(
        "place", sa.Column("osm_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("place", "osm_tags")
    op.drop_column("place", "osm_version")
