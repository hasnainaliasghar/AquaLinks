"""Add the multi-agent layer tables and risk-assessment columns.

Creates:
- ``agent_traces``      — one row per session, full multi-agent execution record.
- ``agent_memory``      — persistent historian notes per water body.
- ``risk_assessments``  — gains ``agent_trace_id`` FK and ``field_brief`` JSONB column.

This migration is **strictly additive and fully reversible**. Every
existing row remains valid; the new columns default to NULL.

When the ``vector`` extension is available, this migration also adds a
typed ``pgvector`` mirror column + HNSW index for faster ANN recall.
If the extension is unavailable (common in lightweight dev DB images),
the migration still succeeds and the app continues with JSON embeddings.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError

from alembic import op

revision: str = "0003_agent_layer"
down_revision: str | None = "0002_aoi_type"
branch_labels = None
depends_on = None


def _dialect_name() -> str:
    return op.get_bind().dialect.name


def _enum_type(name: str, values: list[str]) -> sa.types.TypeEngine:
    """Reuse Postgres enums if present, fall through to SQLAlchemy enum elsewhere."""
    if _dialect_name() == "postgresql":
        return postgresql.ENUM(*values, name=name, create_type=False)
    return sa.Enum(*values, name=name)


def _json_type() -> sa.types.TypeEngine:
    """JSONB on Postgres, JSON everywhere else — same Python API either way."""
    if _dialect_name() == "postgresql":
        return postgresql.JSONB
    return sa.JSON


def _ensure_extension(name: str) -> bool:
    """Best-effort Postgres extension enablement.

    Returns True when the extension exists in the current database.
    Missing extension packages (common in lightweight dev containers)
    should not block the rest of the additive migration.
    """
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return False
    try:
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
    bind = op.get_bind()
    is_postgres = _dialect_name() == "postgresql"
    has_pgvector = False

    if is_postgres:
        # pgvector for the embedding column. Optional in local dev.
        has_pgvector = _ensure_extension("vector")
        if not has_pgvector:
            print("WARNING: vector extension is unavailable; skipping pgvector index acceleration.")

        # Reusable Postgres enum for memory.kind.
        memory_kind = postgresql.ENUM(
            "observation",
            "escalation",
            "false_alarm",
            "evidence_pattern",
            name="memory_kind",
        )
        memory_kind.create(bind, checkfirst=True)

    # agent_traces — one row per session
    op.create_table(
        "agent_traces",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("monitoring_sessions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("coordinator_plan", _json_type(), nullable=False),
        sa.Column("agent_runs", _json_type(), nullable=False),
        sa.Column("total_tokens_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gemini_model", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_traces_session_id", "agent_traces", ["session_id"], unique=True)

    # agent_memory — persistent historian notes per water body
    op.create_table(
        "agent_memory",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "water_body_id",
            sa.Uuid(),
            sa.ForeignKey("water_bodies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_session_id",
            sa.Uuid(),
            sa.ForeignKey("monitoring_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "kind",
            _enum_type(
                "memory_kind",
                ["observation", "escalation", "false_alarm", "evidence_pattern"],
            ),
            nullable=False,
        ),
        sa.Column("note", sa.String(length=500), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("embedding", _json_type(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_memory_water_body_id", "agent_memory", ["water_body_id"])
    op.create_index(
        "ix_agent_memory_water_body_kind_created",
        "agent_memory",
        ["water_body_id", "kind", "created_at"],
    )

    if is_postgres and has_pgvector:
        # Production embedding column — pgvector(768) for text-embedding-004.
        # The JSON ``embedding`` column above stays as the canonical source
        # of truth; this typed column is a denormalised mirror used by the
        # HNSW index. Populated by a trigger so application code only ever
        # writes to the JSON column.
        op.execute("ALTER TABLE agent_memory ADD COLUMN embedding_vec vector(768)")
        op.execute("""
            CREATE OR REPLACE FUNCTION sync_agent_memory_embedding_vec()
            RETURNS trigger AS $$
            BEGIN
              IF NEW.embedding IS NOT NULL THEN
                NEW.embedding_vec := (NEW.embedding)::text::vector;
              ELSE
                NEW.embedding_vec := NULL;
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """)
        op.execute("""
            CREATE TRIGGER agent_memory_embedding_vec_sync
            BEFORE INSERT OR UPDATE OF embedding ON agent_memory
            FOR EACH ROW EXECUTE FUNCTION sync_agent_memory_embedding_vec();
            """)
        # HNSW index for fast cosine-similarity search.
        op.execute(
            "CREATE INDEX ix_agent_memory_embedding_vec "
            "ON agent_memory USING hnsw (embedding_vec vector_cosine_ops)"
        )

    # risk_assessments — new optional columns
    with op.batch_alter_table("risk_assessments") as batch:
        batch.add_column(sa.Column("agent_trace_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("field_brief", _json_type(), nullable=True))
        batch.create_foreign_key(
            "fk_risk_assessments_agent_trace_id",
            "agent_traces",
            ["agent_trace_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index(
            "ix_risk_assessments_agent_trace_id",
            ["agent_trace_id"],
        )


def downgrade() -> None:
    is_postgres = _dialect_name() == "postgresql"

    # risk_assessments — drop the new columns first to release the FK.
    with op.batch_alter_table("risk_assessments") as batch:
        batch.drop_index("ix_risk_assessments_agent_trace_id")
        batch.drop_constraint("fk_risk_assessments_agent_trace_id", type_="foreignkey")
        batch.drop_column("field_brief")
        batch.drop_column("agent_trace_id")

    if is_postgres:
        op.execute("DROP INDEX IF EXISTS ix_agent_memory_embedding_vec")
        op.execute("DROP TRIGGER IF EXISTS agent_memory_embedding_vec_sync ON agent_memory")
        op.execute("DROP FUNCTION IF EXISTS sync_agent_memory_embedding_vec()")

    op.drop_index("ix_agent_memory_water_body_kind_created", table_name="agent_memory")
    op.drop_index("ix_agent_memory_water_body_id", table_name="agent_memory")
    op.drop_table("agent_memory")

    op.drop_index("ix_agent_traces_session_id", table_name="agent_traces")
    op.drop_table("agent_traces")

    if is_postgres:
        op.execute("DROP TYPE IF EXISTS memory_kind")
        # Leave the ``vector`` extension installed; other tables may use it.
