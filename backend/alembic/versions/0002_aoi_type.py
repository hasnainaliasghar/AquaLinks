"""Add AOI water/land classification fields to monitoring_sessions.

Adds two columns:
- ``water_fraction``: float in [0, 1] — fraction of valid pixels in the AOI
  whose NDWI is positive (i.e. open water).
- ``aoi_type``: enum ``water`` / ``mixed`` / ``land`` derived from the
  fraction. Used by the UI and PDF to warn the user when an AOI is
  predominantly land and the water-quality indices are not meaningful.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_aoi_type"
down_revision: str | None = "0001_initial"
branch_labels = None
depends_on = None


def _dialect_name() -> str:
    return op.get_bind().dialect.name


def _enum_type(name: str, values: list[str]) -> sa.types.TypeEngine:
    if _dialect_name() == "postgresql":
        return postgresql.ENUM(*values, name=name, create_type=False)
    return sa.Enum(*values, name=name)


def upgrade() -> None:
    if _dialect_name() == "postgresql":
        aoi_type = postgresql.ENUM("water", "mixed", "land", name="aoi_type")
        aoi_type.create(op.get_bind(), checkfirst=True)

    with op.batch_alter_table("monitoring_sessions") as batch:
        batch.add_column(sa.Column("water_fraction", sa.Float(), nullable=True))
        batch.add_column(
            sa.Column(
                "aoi_type",
                _enum_type("aoi_type", ["water", "mixed", "land"]),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("monitoring_sessions") as batch:
        batch.drop_column("aoi_type")
        batch.drop_column("water_fraction")

    if _dialect_name() == "postgresql":
        op.execute("DROP TYPE IF EXISTS aoi_type")
