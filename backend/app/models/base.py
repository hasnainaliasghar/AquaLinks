"""Base model mixins."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime
from sqlmodel import Field


def utcnow() -> datetime:
    """Return a timezone-aware UTC datetime."""
    return datetime.now(UTC)


class IDMixin:
    """Mixin providing a UUID primary key."""

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)


class TimestampMixin:
    """Mixin providing created_at / updated_at timestamps in UTC."""

    created_at: datetime = Field(
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        nullable=False,
    )
