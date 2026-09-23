"""History tools for the Historian agent.

These are pure DB queries plus a fast trend computation. The Historian
uses ``get_session_history`` to pull every prior session for the water
body (cheap, indexed), then ``compute_trend`` for an immediate linear
regression slope on a chosen metric. For statistical significance the
agent hands the same time series to Gemini's code-execution sandbox
via the ``code_execution`` tool — that lives at the agent layer, not
here.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlmodel import Session, desc, select

from app.models import (
    IndexName,
    MonitoringSession,
    RiskAssessment,
    SessionStatus,
    SpectralIndex,
)


def get_session_history(
    *,
    db: Session,
    water_body_id: UUID,
    limit: int = 20,
) -> dict[str, Any]:
    """Return prior completed sessions for the water body, newest first.

    Each session record bundles the risk row and every aggregated
    spectral index so the Historian can compute trends without
    re-querying.
    """
    statement = (
        select(MonitoringSession)
        .where(MonitoringSession.water_body_id == water_body_id)
        .where(MonitoringSession.status == SessionStatus.COMPLETE)
        # Drop sessions that never completed the imagery fetch — their
        # scene_capture_date is NULL and they would break trend math.
        .where(MonitoringSession.scene_capture_date.is_not(None))  # type: ignore[union-attr]
        .order_by(desc(MonitoringSession.created_at))
        .limit(limit)
    )
    sessions = db.exec(statement).all()
    return {
        "water_body_id": str(water_body_id),
        "count": len(sessions),
        "sessions": [_session_record(db, sess) for sess in sessions],
    }


def compute_trend(
    *,
    metric: str,
    sessions: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Linear regression slope of one metric across the given sessions.

    ``sessions`` is the list shape returned by ``get_session_history``.
    ``metric`` is one of the six spectral index names (case-insensitive)
    or the special name ``"risk_score"``.

    The fit is intentionally elementary — the agent calls
    ``run_trend_significance_test`` (Gemini code execution) when it
    needs a p-value.
    """
    metric_upper = metric.upper()
    points: list[tuple[float, float]] = []
    for record in sessions:
        x = _scene_epoch(record)
        if x is None:
            continue
        if metric_upper == "RISK_SCORE":
            y = (record.get("risk") or {}).get("score")
        else:
            y = _index_value(record.get("indices") or [], metric_upper)
        if y is None:
            continue
        points.append((x, float(y)))

    if len(points) < 2:
        return {
            "metric": metric,
            "n": len(points),
            "slope_per_day": None,
            "intercept": None,
            "first": points[0][1] if points else None,
            "last": points[-1][1] if points else None,
            "note": "need at least two data points to compute a slope",
        }

    # Normalise time to days from the earliest point so the slope reads
    # as "units per day", which is the unit the agent communicates in.
    t0 = min(x for x, _ in points)
    xs = [(x - t0) / 86_400.0 for x, _ in points]
    ys = [y for _, y in points]

    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    den = sum((x - mean_x) ** 2 for x in xs)
    if den == 0:
        return {
            "metric": metric,
            "n": n,
            "slope_per_day": 0.0,
            "intercept": mean_y,
            "first": ys[0],
            "last": ys[-1],
            "note": "all samples share the same timestamp",
        }
    slope = num / den
    intercept = mean_y - slope * mean_x
    return {
        "metric": metric,
        "n": n,
        "slope_per_day": slope,
        "intercept": intercept,
        "first": ys[0],
        "last": ys[-1],
        "span_days": max(xs) - min(xs),
    }


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _session_record(db: Session, sess: MonitoringSession) -> dict[str, Any]:
    """Bundle a session with its risk row and aggregated indices."""
    risk = db.exec(select(RiskAssessment).where(RiskAssessment.session_id == sess.id)).first()
    indices = db.exec(select(SpectralIndex).where(SpectralIndex.session_id == sess.id)).all()
    return {
        "session_id": str(sess.id),
        "scene_capture_date": (
            sess.scene_capture_date.isoformat() if sess.scene_capture_date else None
        ),
        "scene_id": sess.scene_id,
        "cloud_cover": sess.scene_cloud_cover,
        "aoi_type": sess.aoi_type.value if sess.aoi_type else None,
        "water_fraction": sess.water_fraction,
        "risk": (
            {
                "score": risk.score,
                "level": risk.level.value,
                "urgency": risk.urgency.value,
            }
            if risk
            else None
        ),
        "indices": [
            {"name": idx.name.value, "value": idx.value} for idx in indices if idx.value is not None
        ],
    }


def _scene_epoch(record: dict[str, Any]) -> float | None:
    """Epoch seconds for the scene capture date, or None when unknown."""
    iso = record.get("scene_capture_date")
    if not iso:
        return None
    from datetime import datetime

    try:
        return datetime.fromisoformat(iso).timestamp()
    except ValueError:
        return None


def _index_value(indices: Sequence[dict[str, Any]], name_upper: str) -> float | None:
    valid_names = {n.value for n in IndexName}
    if name_upper not in valid_names:
        return None
    for entry in indices:
        if str(entry.get("name", "")).upper() == name_upper:
            return entry.get("value")
    return None


__all__ = ["compute_trend", "get_session_history"]
