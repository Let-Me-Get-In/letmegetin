"""Add the AccesLibre identifiers we used to drop: rnb_id, siret, numero, voie.

Revision ID: 0016
Revises: 0015
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("place", sa.Column("rnb_id", sa.String(12), nullable=True))
    op.add_column("place", sa.Column("siret", sa.String(14), nullable=True))
    op.add_column("place", sa.Column("address_number", sa.String(32), nullable=True))
    op.add_column("place", sa.Column("address_street", sa.String(255), nullable=True))
    # The duplicate pass compares neighbours by building: a lookup on rnb_id is enough.
    op.create_index("ix_place_rnb_id", "place", ["rnb_id"])


def downgrade() -> None:
    op.drop_index("ix_place_rnb_id", table_name="place")
    op.drop_column("place", "address_street")
    op.drop_column("place", "address_number")
    op.drop_column("place", "siret")
    op.drop_column("place", "rnb_id")
