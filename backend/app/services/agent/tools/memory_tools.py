"""Persistent-memory tools for the Historian agent.

These let the Historian read its own notes from prior sessions and
write new ones. The notes live in the ``agent_memory`` table; each
write also generates a text-embedding-004 vector so future Historian
calls can recall semantically related notes, not just the most recent
ones.

On Postgres the production deployment uses the pgvector ANN index
(added by migration 0003). The Python ``semantic_recall_notes`` here
performs an explicit cosine similarity in user-space; the index makes
the query fast but doesn't change the result shape. On SQLite (tests)
there is no index — we do the same Python similarity over a small set
of rows.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlmodel import Session, desc, select

from app.core.logging import get_logger
from app.models import AgentMemory, MemoryKind
from app.services.agent.tools.embeddings import cosine_similarity, embed_text

LOGGER = get_logger(__name__)

# Per-water-body retention: keep at most this many active notes.
# Older notes are soft-archived inside ``write_persistent_note`` so the
# Historian's recall queries don't drift into ancient irrelevant context.
MAX_ACTIVE_NOTES_PER_WATER_BODY = 50


def recall_persistent_notes(
    *,
    db: Session,
    water_body_id: UUID,
    kinds: list[MemoryKind] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Return the most recent active notes for a water body."""
    statement = (
        select(AgentMemory)
        .where(AgentMemory.water_body_id == water_body_id)
        .where(AgentMemory.archived_at.is_(None))  # type: ignore[union-attr]
    )
    if kinds:
        statement = statement.where(AgentMemory.kind.in_(kinds))  # type: ignore[union-attr]
    statement = statement.order_by(desc(AgentMemory.created_at)).limit(max(limit, 1))
    rows = db.exec(statement).all()
    return {
        "water_body_id": str(water_body_id),
        "count": len(rows),
        "notes": [row.as_recall_payload() for row in rows],
    }


def semantic_recall_notes(
    *,
    db: Session,
    water_body_id: UUID,
    query: str,
    top_k: int = 5,
    candidate_pool: int = 100,
) -> dict[str, Any]:
    """Return the top-k notes most similar to ``query``.

    Pulls up to ``candidate_pool`` recent notes from the DB and ranks
    them by cosine similarity in Python. The pgvector HNSW index on
    Postgres is used implicitly by ``candidate_pool`` queries planned
    by future-PG-native variants — keeping the user-space ranking here
    means the same code path runs identically on SQLite and Postgres.
    """
    query_vec = embed_text(query)

    statement = (
        select(AgentMemory)
        .where(AgentMemory.water_body_id == water_body_id)
        .where(AgentMemory.archived_at.is_(None))  # type: ignore[union-attr]
        .order_by(desc(AgentMemory.created_at))
        .limit(max(candidate_pool, top_k))
    )
    rows = db.exec(statement).all()

    scored: list[tuple[float, AgentMemory]] = []
    for row in rows:
        if not row.embedding:
            continue
        score = cosine_similarity(query_vec, row.embedding)
        scored.append((score, row))
    scored.sort(key=lambda pair: pair[0], reverse=True)

    top = scored[: max(top_k, 1)]
    return {
        "water_body_id": str(water_body_id),
        "query": query,
        "matches": [
            {**row.as_recall_payload(), "similarity": round(score, 4)} for score, row in top
        ],
    }


def write_persistent_note(
    *,
    db: Session,
    water_body_id: UUID,
    source_session_id: UUID,
    kind: MemoryKind | str,
    note: str,
    confidence: float,
) -> dict[str, Any]:
    """Append a new note and embed it. Returns the persisted record summary."""
    kind_enum = MemoryKind(kind) if isinstance(kind, str) else kind
    trimmed = note.strip()
    if not trimmed:
        return {"created": False, "reason": "note is empty"}
    if not 0.0 <= confidence <= 1.0:
        return {"created": False, "reason": "confidence must be in [0, 1]"}

    embedding = embed_text(trimmed)
    record = AgentMemory(
        water_body_id=water_body_id,
        source_session_id=source_session_id,
        kind=kind_enum,
        note=trimmed[:500],
        confidence=float(confidence),
        embedding=embedding,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    _archive_overflow(db, water_body_id)

    return {
        "created": True,
        "id": str(record.id),
        "kind": record.kind.value,
        "confidence": round(record.confidence, 3),
    }


def _archive_overflow(db: Session, water_body_id: UUID) -> None:
    """Soft-archive notes beyond the retention window.

    Keeps the most recent ``MAX_ACTIVE_NOTES_PER_WATER_BODY`` active
    notes per water body. Anything older flips ``archived_at`` so the
    recall queries skip it without losing the audit history.
    """
    active = db.exec(
        select(AgentMemory)
        .where(AgentMemory.water_body_id == water_body_id)
        .where(AgentMemory.archived_at.is_(None))  # type: ignore[union-attr]
        .order_by(desc(AgentMemory.created_at))
    ).all()
    overflow = active[MAX_ACTIVE_NOTES_PER_WATER_BODY:]
    if not overflow:
        return
    now = datetime.now(UTC)
    for stale in overflow:
        stale.archived_at = now
        db.add(stale)
    db.commit()
    LOGGER.info("Archived %d overflow notes for water_body=%s", len(overflow), water_body_id)


__all__ = [
    "MAX_ACTIVE_NOTES_PER_WATER_BODY",
    "recall_persistent_notes",
    "semantic_recall_notes",
    "write_persistent_note",
]
