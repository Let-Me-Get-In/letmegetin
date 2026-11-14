"""append-only export journal with an MVCC transaction-id boundary

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSONB = postgresql.JSONB(astext_type=sa.Text())


class XID8(sa.types.UserDefinedType):
    """PostgreSQL ``xid8``; SQLAlchemy has no native type and the boundary compares in it."""

    cache_ok = True

    def get_col_spec(self, **kw: object) -> str:
        return "XID8"


def upgrade() -> None:
    op.create_table(
        "export_event",
        sa.Column("seq", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            "xid",
            XID8(),
            server_default=sa.text("pg_current_xact_id()"),
            nullable=False,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("entity", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("op", sa.String(length=16), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("payload", _JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.CheckConstraint(
            "entity IN ('place','place_accessibility')", name="export_event_entity_ck"
        ),
        sa.CheckConstraint("op IN ('insert','update','merge')", name="export_event_op_ck"),
        sa.PrimaryKeyConstraint("seq"),
    )
    op.create_index("ix_export_event_entity_id_seq", "export_event", ["entity_id", "seq"])


def downgrade() -> None:
    op.drop_index("ix_export_event_entity_id_seq", table_name="export_event")
    op.drop_table("export_event")
