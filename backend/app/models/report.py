"""Generated report record."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Column, ForeignKey, String
from sqlmodel import Field, SQLModel

from app.models.base import IDMixin, TimestampMixin


class Report(IDMixin, TimestampMixin, SQLModel, table=True):
    """A rendered PDF report cached on local disk."""

    __tablename__ = "reports"

    session_id: UUID = Field(
        sa_column=Column(
            ForeignKey("monitoring_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            unique=True,
        )
    )
    file_path: str = Field(sa_column=Column(String(500), nullable=False))
    byte_size: int = Field(default=0, ge=0)
    content_type: str = Field(default="application/pdf", sa_column=Column(String(80)))
