"""reviewed per-licence attribution sentence for the open export

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # No backfill: data/referential/licences.csv is the source of truth and the next
    # `admin licences sync` carries the reviewed sentence in (LIC-05).
    op.add_column("licence", sa.Column("attribution_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("licence", "attribution_text")
