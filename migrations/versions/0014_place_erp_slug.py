"""AccesLibre ERP slug on place (the identifier the probe resolves)

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Stays NULL until the 15-03 probe records a `slug` rule and 15-04 re-imports the column.
    op.add_column("place", sa.Column("erp_slug", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("place", "erp_slug")
