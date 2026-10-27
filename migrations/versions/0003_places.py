"""places, deduplication, category mapping and precomputed grids

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-27
"""

from __future__ import annotations

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSONB = postgresql.JSONB(astext_type=sa.Text())
_FAMILIES = postgresql.ARRAY(sa.String(length=16))

# Denormalized lat/lng are the source of truth; PostGIS derives the point, so the two
# can never drift and the importer never has to build a WKT value.
_LOCATION = (
    "CASE WHEN lat IS NOT NULL AND lng IS NOT NULL "
    "THEN ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography END"
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "place",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_normalized", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=300), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("address_full", sa.String(length=500), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("postal_code", sa.String(length=16), nullable=True),
        sa.Column("country_code", sa.String(length=2), server_default="FR", nullable=False),
        sa.Column("lat", sa.Double(), nullable=True),
        sa.Column("lng", sa.Double(), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            sa.Computed(_LOCATION, persisted=True),
            nullable=True,
        ),
        sa.Column("operating_status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("confidence", sa.Double(), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("canonical_id", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["canonical_id"], ["place.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_place_slug", "place", ["slug"], unique=True)
    op.create_index("ix_place_category_id", "place", ["category_id"], unique=False)
    op.create_index("ix_place_canonical_id", "place", ["canonical_id"], unique=False)
    op.create_index(
        "place_source_source_id_uc",
        "place",
        ["source", "source_id"],
        unique=True,
        postgresql_where=sa.text("source_id IS NOT NULL"),
    )
    op.create_index("ix_place_location", "place", ["location"], postgresql_using="gist")
    op.create_index(
        "ix_place_name_normalized",
        "place",
        ["name_normalized"],
        postgresql_using="gin",
        postgresql_ops={"name_normalized": "gin_trgm_ops"},
    )

    op.create_table(
        "place_alias",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["place_id"], ["place.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_place_alias_place_id", "place_alias", ["place_id"], unique=False)

    op.create_table(
        "place_merge_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("kept_id", sa.Integer(), nullable=False),
        sa.Column("merged_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Double(), nullable=False),
        sa.Column("actor", sa.String(length=32), server_default="importer", nullable=False),
        sa.Column("created", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["kept_id"], ["place.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["merged_id"], ["place.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_place_merge_log_kept_id", "place_merge_log", ["kept_id"], unique=False)

    op.create_table(
        "place_accessibility",
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("criterion_id", sa.Integer(), nullable=False),
        sa.Column("value", _JSONB, nullable=False),
        sa.ForeignKeyConstraint(["place_id"], ["place.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["criterion_id"], ["criteria.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("place_id", "criterion_id"),
    )

    op.add_column(
        "criteria",
        sa.Column("handicap_families", _FAMILIES, server_default=sa.text("'{}'"), nullable=False),
    )
    op.add_column("criteria", sa.Column("en17210_ref", sa.String(length=64), nullable=True))
    op.add_column(
        "accessibility_filters",
        sa.Column("handicap_families", _FAMILIES, server_default=sa.text("'{}'"), nullable=False),
    )

    op.create_table(
        "category_mapping",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("overture_category", sa.String(length=120), nullable=True),
        sa.Column("osm_tag", sa.String(length=120), nullable=True),
        sa.Column("acceslibre_family", sa.String(length=60), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category_id", name="category_mapping_category_uc"),
    )

    op.create_table(
        "category_grid",
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("tree", _JSONB, nullable=False),
        sa.Column("updated", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("category_id"),
    )

    op.create_table(
        "referential_version",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("INSERT INTO referential_version (id, version) VALUES (1, 1)")


def downgrade() -> None:
    op.drop_table("referential_version")
    op.drop_table("category_grid")
    op.drop_table("category_mapping")
    op.drop_column("accessibility_filters", "handicap_families")
    op.drop_column("criteria", "en17210_ref")
    op.drop_column("criteria", "handicap_families")
    op.drop_table("place_accessibility")
    op.drop_index("ix_place_merge_log_kept_id", table_name="place_merge_log")
    op.drop_table("place_merge_log")
    op.drop_index("ix_place_alias_place_id", table_name="place_alias")
    op.drop_table("place_alias")
    op.drop_index("ix_place_name_normalized", table_name="place")
    op.drop_index("ix_place_location", table_name="place")
    op.drop_index("place_source_source_id_uc", table_name="place")
    op.drop_index("ix_place_canonical_id", table_name="place")
    op.drop_index("ix_place_category_id", table_name="place")
    op.drop_index("ix_place_slug", table_name="place")
    op.drop_table("place")
