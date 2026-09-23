"""Pydantic v2 request/response schemas."""

from app.schemas.evidence import EvidenceCreate, EvidenceRead
from app.schemas.indices import SpectralIndexRead
from app.schemas.report import ReportRead
from app.schemas.risk import RiskAssessmentRead
from app.schemas.session import (
    SessionCreate,
    SessionDetailRead,
    SessionListItem,
    SessionStatusRead,
)
from app.schemas.water_body import (
    WaterBodyBulkDelete,
    WaterBodyBulkDeleteResult,
    WaterBodyCreate,
    WaterBodyRead,
    WaterBodyUpdate,
)

__all__ = [
    "EvidenceCreate",
    "EvidenceRead",
    "ReportRead",
    "RiskAssessmentRead",
    "SessionCreate",
    "SessionDetailRead",
    "SessionListItem",
    "SessionStatusRead",
    "SpectralIndexRead",
    "WaterBodyBulkDelete",
    "WaterBodyBulkDeleteResult",
    "WaterBodyCreate",
    "WaterBodyRead",
    "WaterBodyUpdate",
]
