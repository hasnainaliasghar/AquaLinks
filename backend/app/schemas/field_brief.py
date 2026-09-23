"""DTOs for the Field Liaison's structured handoff.

Kept in ``schemas`` so the API layer can re-export the same Pydantic
models without pulling in the agent runtime.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Priority = Literal["p0", "p1", "p2"]


class FieldLocation(BaseModel):
    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)
    description: str


class FieldTask(BaseModel):
    priority: Priority
    location: FieldLocation
    sample_type: str
    equipment: list[str] = Field(default_factory=list)
    photo_prompts: list[str] = Field(default_factory=list)
    estimated_minutes: int = Field(gt=0)


class FieldBrief(BaseModel):
    """Structured operations handoff produced by the Field Liaison agent."""

    tasks: list[FieldTask] = Field(default_factory=list)
    turnaround_hours: int = Field(gt=0)
    escalate_to: str | None = None


__all__ = ["FieldBrief", "FieldLocation", "FieldTask", "Priority"]
