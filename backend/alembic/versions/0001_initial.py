"""Initial AquaLens schema.

Creates the six core tables (water_bodies, monitoring_sessions,
spectral_indices, field_evidence, risk_assessments, reports) and
enables the PostGIS extension when running against Postgres.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels = None
depends_on = None


def _dialect_name() -> str:
    bind = op.get_bind()
    return bind.dialect.name


def _enum_type(name: str, values: list[str]) -> sa.types.TypeEngine:
    """Return a typed Enum, using a Postgres ENUM when available."""
    if _dialect_name() == "postgresql":
        return postgresql.ENUM(*values, name=name, create_type=False)
    return sa.Enum(*values, name=name)


def _ensure_extension(name: str) -> bool:
    """Best-effort Postgres extension enablement.

    Returns True when ``name`` is installed in the current database.
    If the extension package is unavailable (common in local/dev DB
    images), migration continues with a warning-friendly False.
    """
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return False
    try:
        # Run extension DDL in autocommit mode so a failure does not
        # poison the migration transaction.
        with op.get_context().autocommit_block():
            op.execute(f"CREATE EXTENSION IF NOT EXISTS {name}")
    except SQLAlchemyError:
        pass
    row = bind.execute(
        sa.text("SELECT 1 FROM pg_extension WHERE extname = :name"),
        {"name": name},
    ).first()
    return row is not None


def upgrade() -> None:
    dialect = _dialect_name()

    if dialect == "postgresql":
        postgis_enabled = _ensure_extension("postgis")
        if not postgis_enabled:
            print("WARNING: postgis extension is unavailable; continuing with JSON geometry only.")

        # Pre-create enums so SQLAlchemy doesn't issue CREATE TYPE per column.
        session_status = postgresql.ENUM(
            "pending",
            "processing",
            "awaiting_evidence",
            "complete",
            "failed",
            name="session_status",
        )
        session_status.create(op.get_bind(), checkfirst=True)

        index_name = postgresql.ENUM(
            "NDWI", "MNDWI", "NDTI", "NDCI", "NDVI", "WRI", name="index_name"
        )
        index_name.create(op.get_bind(), checkfirst=True)

        water_color = postgresql.ENUM(
            "clear",
            "blue",
            "green",
            "brown",
            "yellow",
            "red",
            "black",
            "other",
            name="water_color",
        )
        water_color.create(op.get_bind(), checkfirst=True)

        water_odor = postgresql.ENUM(
            "none",
            "earthy",
            "musty",
            "fishy",
            "rotten",
            "chemical",
            "sewage",
            "other",
            name="water_odor",
        )
        water_odor.create(op.get_bind(), checkfirst=True)

        risk_level = postgresql.ENUM("low", "medium", "high", name="risk_level")
        risk_level.create(op.get_bind(), checkfirst=True)

        risk_urgency = postgresql.ENUM("routine", "elevated", "immediate", name="risk_urgency")
        risk_urgency.create(op.get_bind(), checkfirst=True)

    # --- water_bodies ---
    op.create_table(
        "water_bodies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False, index=True),
        sa.Column("description", sa.String(1000)),
        sa.Column(
            "geometry",
            postgresql.JSONB() if dialect == "postgresql" else sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "centroid",
            postgresql.JSONB() if dialect == "postgresql" else sa.JSON(),
        ),
        sa.Column("area_km2", sa.Float()),
        sa.Column("source", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- monitoring_sessions ---
    op.create_table(
        "monitoring_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "water_body_id",
            sa.Uuid(),
            sa.ForeignKey("water_bodies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("max_cloud_cover", sa.Float(), nullable=False, server_default="30"),
        sa.Column(
            "status",
            _enum_type(
                "session_status",
                ["pending", "processing", "awaiting_evidence", "complete", "failed"],
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("status_message", sa.String(500)),
        sa.Column("scene_id", sa.String(120)),
        sa.Column("scene_capture_date", sa.DateTime(timezone=True)),
        sa.Column("scene_cloud_cover", sa.Float()),
        sa.Column("scene_provider", sa.String(60)),
        sa.Column("scene_thumbnail_url", sa.String(500)),
        sa.Column(
            "scene_metadata",
            postgresql.JSONB() if dialect == "postgresql" else sa.JSON(),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- spectral_indices ---
    op.create_table(
        "spectral_indices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("monitoring_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "name",
            _enum_type("index_name", ["NDWI", "MNDWI", "NDTI", "NDCI", "NDVI", "WRI"]),
            nullable=False,
        ),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("min_value", sa.Float()),
        sa.Column("max_value", sa.Float()),
        sa.Column("stddev", sa.Float()),
        sa.Column("interpretation", sa.String(280)),
        sa.Column(
            "bands",
            postgresql.JSONB() if dialect == "postgresql" else sa.JSON(),
            nullable=False,
        ),
        sa.Column("sample_count", sa.Integer()),
        sa.Column(
            "extra",
            postgresql.JSONB() if dialect == "postgresql" else sa.JSON(),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_spectral_indices_session_name",
        "spectral_indices",
        ["session_id", "name"],
        unique=True,
    )

    # --- field_evidence ---
    op.create_table(
        "field_evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("monitoring_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "water_color",
            _enum_type(
                "water_color",
                ["clear", "blue", "green", "brown", "yellow", "red", "black", "other"],
            ),
            nullable=False,
        ),
        sa.Column(
            "odor",
            _enum_type(
                "water_odor",
                ["none", "earthy", "musty", "fishy", "rotten", "chemical", "sewage", "other"],
            ),
            nullable=False,
        ),
        sa.Column("algae_present", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("dead_fish_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rainfall_mm", sa.Float(), nullable=False, server_default="0"),
        sa.Column("complaints_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.String(2000)),
        sa.Column("photo_url", sa.String(500)),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("reporter_name", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- risk_assessments ---
    op.create_table(
        "risk_assessments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("monitoring_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column(
            "level",
            _enum_type("risk_level", ["low", "medium", "high"]),
            nullable=False,
        ),
        sa.Column(
            "urgency",
            _enum_type("risk_urgency", ["routine", "elevated", "immediate"]),
            nullable=False,
        ),
        sa.Column("recommendation", sa.String(1200), nullable=False),
        sa.Column("reasoning", sa.String(4000), nullable=False),
        sa.Column("limitations", sa.String(2000), nullable=False),
        sa.Column(
            "contributors",
            postgresql.JSONB() if dialect == "postgresql" else sa.JSON(),
            nullable=False,
        ),
        sa.Column("model_id", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- reports ---
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("monitoring_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            unique=True,
        ),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_type", sa.String(80), nullable=False, server_default="application/pdf"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("risk_assessments")
    op.drop_table("field_evidence")
    op.drop_index("ix_spectral_indices_session_name", table_name="spectral_indices")
    op.drop_table("spectral_indices")
    op.drop_table("monitoring_sessions")
    op.drop_table("water_bodies")

    if _dialect_name() == "postgresql":
        for enum_name in (
            "risk_urgency",
            "risk_level",
            "water_odor",
            "water_color",
            "index_name",
            "session_status",
        ):
            op.execute(f"DROP TYPE IF EXISTS {enum_name}")
