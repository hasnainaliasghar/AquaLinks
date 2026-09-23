"""End-to-end monitoring pipeline.

Each step is a function over the database. The :func:`run_full` entry
point is what the API's ``BackgroundTasks`` invokes after creating a
session. Re-running ``run_full`` is idempotent: existing rows for the
session are cleared before new ones are written.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session as DBSession
from sqlmodel import Session

from app.core.database import get_engine
from app.core.logging import get_logger
from app.models.agent_trace import AgentTrace
from app.models.evidence import FieldEvidence
from app.models.risk_assessment import RiskAssessment
from app.models.session import AOIType, MonitoringSession, SessionStatus
from app.models.spectral_index import SpectralIndex
from app.models.water_body import WaterBody
from app.services import reasoning
from app.services.indices import IndexAggregate, compute_all
from app.services.report_generator import (
    persist_report,
    render_report_html,
    render_report_pdf,
)
from app.services.risk_model import RiskScore, score_risk
from app.services.satellite.base import ImageryBundle
from app.services.satellite.factory import get_satellite_provider

LOGGER = get_logger(__name__)


def _open_session() -> DBSession:
    return Session(get_engine())


def _load_session_and_water_body(
    db: DBSession, session_id: UUID
) -> tuple[MonitoringSession, WaterBody]:
    sess = db.get(MonitoringSession, session_id)
    if sess is None:
        raise LookupError(f"session {session_id} not found")
    wb = db.get(WaterBody, sess.water_body_id)
    if wb is None:
        raise LookupError(f"water body {sess.water_body_id} not found")
    return sess, wb


def _set_status(
    db: DBSession,
    sess: MonitoringSession,
    status: SessionStatus,
    message: str | None = None,
) -> None:
    sess.status = status
    sess.status_message = message
    db.add(sess)
    db.commit()


def retrieve_imagery(sess: MonitoringSession, water_body: WaterBody) -> ImageryBundle:
    """Step 2 — fetch a Sentinel-2 scene clipped to the AOI."""
    provider = get_satellite_provider()
    return provider.fetch(
        geometry=water_body.geometry,
        start_date=sess.start_date,
        end_date=sess.end_date,
        max_cloud_cover=sess.max_cloud_cover,
    )


# Thresholds for the AOI water/land classification. Two cuts on the
# fraction of NDWI-positive pixels in the AOI:
#   >= 0.50  → primarily water (analysis is meaningful as designed)
#   >= 0.20  → mixed water/land (indices reflect both surfaces)
#   <  0.20  → primarily land (water-quality indices are not meaningful)
WATER_FRACTION_WATER_THRESHOLD = 0.50
WATER_FRACTION_MIXED_THRESHOLD = 0.20


def _classify_aoi(water_fraction: float) -> AOIType:
    if water_fraction >= WATER_FRACTION_WATER_THRESHOLD:
        return AOIType.WATER
    if water_fraction >= WATER_FRACTION_MIXED_THRESHOLD:
        return AOIType.MIXED
    return AOIType.LAND


def _store_aoi_classification(
    db: DBSession, sess: MonitoringSession, water_fraction: float
) -> None:
    sess.water_fraction = float(water_fraction)
    sess.aoi_type = _classify_aoi(water_fraction)
    db.add(sess)
    db.commit()


def store_imagery_metadata(db: DBSession, sess: MonitoringSession, bundle: ImageryBundle) -> None:
    sess.scene_id = bundle.scene_id
    sess.scene_capture_date = bundle.capture_date
    sess.scene_cloud_cover = bundle.cloud_cover
    sess.scene_provider = bundle.provider
    sess.scene_thumbnail_url = bundle.thumbnail_url
    sess.scene_metadata = bundle.metadata
    db.add(sess)
    db.commit()


def store_indices(
    db: DBSession, sess: MonitoringSession, aggregates: Iterable[IndexAggregate]
) -> list[SpectralIndex]:
    """Step 3 — replace any existing indices for this session and persist."""
    db.query(SpectralIndex).filter(SpectralIndex.session_id == sess.id).delete()
    db.commit()

    rows: list[SpectralIndex] = []
    for agg in aggregates:
        row = SpectralIndex(
            session_id=sess.id,
            name=agg.name,
            value=agg.value,
            min_value=agg.min_value,
            max_value=agg.max_value,
            stddev=agg.stddev,
            interpretation=agg.interpretation,
            bands=agg.bands,
            sample_count=agg.sample_count,
        )
        db.add(row)
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def _existing_evidence(db: DBSession, sess: MonitoringSession) -> list[FieldEvidence]:
    return (
        db.query(FieldEvidence)
        .filter(FieldEvidence.session_id == sess.id)
        .order_by(FieldEvidence.created_at.desc())
        .all()
    )


def upsert_risk_assessment(
    db: DBSession,
    sess: MonitoringSession,
    water_body: WaterBody,
    indices: list[SpectralIndex],
    score: RiskScore,
    bundle: reasoning.ReasoningBundle,
    model_id: str,
    *,
    agent_trace_id: UUID | None = None,
    reporter_summary: dict | None = None,
    replace_reporter_summary: bool = False,
) -> RiskAssessment:
    existing = db.query(RiskAssessment).filter(RiskAssessment.session_id == sess.id).one_or_none()
    if existing is None:
        existing = RiskAssessment(
            session_id=sess.id,
            score=score.score,
            level=score.level,
            urgency=score.urgency,
            recommendation=bundle.recommendation,
            reasoning=bundle.reasoning,
            limitations=bundle.limitations,
            contributors=score.contributors,
            model_id=model_id,
            agent_trace_id=agent_trace_id,
            field_brief=reporter_summary,
        )
        db.add(existing)
    else:
        existing.score = score.score
        existing.level = score.level
        existing.urgency = score.urgency
        existing.recommendation = bundle.recommendation
        existing.reasoning = bundle.reasoning
        existing.limitations = bundle.limitations
        existing.contributors = score.contributors
        existing.model_id = model_id
        # Only overwrite agent metadata when the new run produced one;
        # this lets a fallback to the deterministic narrator preserve
        # the previous trace rather than nulling it out.
        if agent_trace_id is not None:
            existing.agent_trace_id = agent_trace_id
        if replace_reporter_summary or reporter_summary is not None:
            existing.field_brief = reporter_summary
    db.commit()
    db.refresh(existing)
    return existing


def generate_and_store_report(
    db: DBSession,
    sess: MonitoringSession,
    water_body: WaterBody,
    indices: list[SpectralIndex],
    evidence: list[FieldEvidence],
    risk: RiskAssessment,
) -> None:
    html = render_report_html(
        session=sess,
        water_body=water_body,
        indices=indices,
        evidence=evidence,
        risk=risk,
    )
    pdf_bytes = render_report_pdf(html)
    persist_report(db, session=sess, pdf_bytes=pdf_bytes)


def score_and_explain(
    db: DBSession,
    sess: MonitoringSession,
    water_body: WaterBody,
    indices: list[SpectralIndex],
) -> RiskAssessment:
    """Steps 4–6: compute the numeric score, get an LLM narrative, persist."""

    evidence = _existing_evidence(db, sess)

    aggregates = [
        IndexAggregate(
            name=row.name,
            value=row.value,
            min_value=row.min_value or 0.0,
            max_value=row.max_value or 0.0,
            stddev=row.stddev or 0.0,
            sample_count=row.sample_count or 0,
            interpretation=row.interpretation or "",
            bands=row.bands,
        )
        for row in indices
    ]

    score = score_risk(aggregates, evidence)

    from app.core.config import get_settings  # local import to keep module light

    settings = get_settings()
    agent_trace_id: UUID | None = None
    reporter_summary_payload: dict | None = None

    # Agentic path: orchestrator runs all four sub-agents, persists the
    # trace, and returns the narrative + Reporter summary. Single-call
    # ``generate_reasoning`` remains the fallback for ``AQUALENS_FAKE_GEMINI``
    # mode and when the agentic flag is off.
    #
    # When the AOI isn't water (the polygon is over land or only
    # partially covers water) we skip the agent layer entirely: the
    # Analyst would only end up saying "this isn't water" which is
    # information the deterministic citizen summary already conveys.
    # Burning Gemini tokens on it would be wasted.
    aoi_is_water = sess.aoi_type is None or sess.aoi_type.value == "water"
    use_agentic = (
        settings.aqualens_agentic_mode
        and not settings.aqualens_fake_gemini
        and bool(settings.gemini_api_keys)
        and aoi_is_water
    )
    if not aoi_is_water:
        LOGGER.info(
            "Session %s: AOI is %s — skipping agent layer to save tokens.",
            sess.id,
            sess.aoi_type.value if sess.aoi_type else "unknown",
        )
    if use_agentic:
        # Deterministic indices + numeric score are ready at this
        # point; surface an explicit handover stage before agent
        # progress messages start streaming in.
        sess.status_message = "Handing over to coordinator"
        db.add(sess)
        db.commit()
        try:
            bundle, agent_trace_id, reporter_summary_payload = _run_agent_layer(
                db=db,
                sess=sess,
                water_body=water_body,
                aggregates=aggregates,
                evidence=evidence,
                score=score,
            )
        except Exception as exc:
            LOGGER.warning(
                "Agent layer failed for session %s (%s); falling back to single-call reasoning",
                sess.id,
                exc,
            )
            bundle = reasoning.generate_reasoning(
                score=score,
                indices=aggregates,
                evidence=evidence,
                water_body=water_body,
                water_fraction=sess.water_fraction,
                aoi_type=sess.aoi_type.value if sess.aoi_type else None,
            )
    else:
        bundle = reasoning.generate_reasoning(
            score=score,
            indices=aggregates,
            evidence=evidence,
            water_body=water_body,
            water_fraction=sess.water_fraction,
            aoi_type=sess.aoi_type.value if sess.aoi_type else None,
        )

    return upsert_risk_assessment(
        db,
        sess,
        water_body,
        indices,
        score,
        bundle,
        model_id=(
            "aqualens-fake-narrator" if settings.aqualens_fake_gemini else settings.gemini_model
        ),
        agent_trace_id=agent_trace_id,
        reporter_summary=reporter_summary_payload,
        replace_reporter_summary=True,
    )


def _run_agent_layer(
    *,
    db: DBSession,
    sess: MonitoringSession,
    water_body: WaterBody,
    aggregates: list[IndexAggregate],
    evidence: list[FieldEvidence],
    score: RiskScore,
) -> tuple[reasoning.ReasoningBundle, UUID | None, dict | None]:
    """Run the multi-agent flow and persist the trace.

    Returns the final ``ReasoningBundle`` (always), the new
    ``AgentTrace.id`` (when persistence succeeded), and the Reporter
    summary payload (when produced).
    """
    from app.services.agent.orchestrator import run_orchestrator

    indices_payload = [
        {
            "name": agg.name.value,
            "value": agg.value,
            "min_value": agg.min_value,
            "max_value": agg.max_value,
            "stddev": agg.stddev,
            "sample_count": agg.sample_count,
            "interpretation": agg.interpretation,
            "bands": agg.bands,
        }
        for agg in aggregates
    ]
    risk_payload = {
        "score": score.score,
        "level": score.level.value,
        "urgency": score.urgency.value,
        "contributors": score.contributors,
    }
    aoi_payload = {
        "type": sess.aoi_type.value if sess.aoi_type else None,
        "water_fraction": sess.water_fraction,
    }
    evidence_payload = [
        {
            "water_color": ev.water_color.value,
            "odor": ev.odor.value,
            "algae_present": ev.algae_present,
            "dead_fish_count": ev.dead_fish_count,
            "rainfall_mm": ev.rainfall_mm,
            "complaints_count": ev.complaints_count,
            "notes": ev.notes,
            "reported_at": ev.created_at.isoformat() if ev.created_at else None,
        }
        for ev in evidence
    ]

    prior_session_count = (
        db.query(MonitoringSession)
        .filter(MonitoringSession.water_body_id == water_body.id)
        .filter(MonitoringSession.status == SessionStatus.COMPLETE)
        .filter(MonitoringSession.id != sess.id)
        .count()
    )

    # Each agent emits a progress event when it starts and when it
    # finishes. We translate the structured event into both a
    # human-readable ``status_message`` (animates the existing status
    # pill) and an incremental upsert of the agent_traces row (lets
    # the Agent Trace card render the timeline as it builds).
    trace_box: dict[str, AgentTrace | None] = {"row": None}

    def _persist_progress(event: dict[str, Any]) -> None:
        phase = event.get("phase")
        agent = str(event.get("agent") or "")
        trace_payload = event.get("trace") or {}

        if phase == "started":
            sess.status_message = _AGENT_RUNNING_LABELS.get(
                agent, f"Agent running — {agent.replace('_', ' ')}…"
            )
            db.add(sess)
            db.commit()
        elif phase == "completed":
            trace_box["row"] = _upsert_agent_trace_row(db, sess, trace_payload, trace_box["row"])
            label = _AGENT_DONE_LABELS.get(agent, f"Agent finished — {agent.replace('_', ' ')}")
            sess.status_message = label
            db.add(sess)
            db.commit()

    result = run_orchestrator(
        db=db,
        water_body=water_body,
        session_id=sess.id,
        aoi_geojson=water_body.geometry or {},
        start_date=sess.start_date.isoformat(),
        end_date=sess.end_date.isoformat(),
        max_cloud_cover=sess.max_cloud_cover,
        indices=indices_payload,
        risk=risk_payload,
        aoi=aoi_payload,
        evidence=evidence_payload,
        prior_session_count=prior_session_count,
        scene_id=sess.scene_id,
        scene_capture_date=(
            sess.scene_capture_date.isoformat() if sess.scene_capture_date else None
        ),
        scene_cloud_cover=sess.scene_cloud_cover,
        on_progress=_persist_progress,
    )

    # Final write — covers the case where ``on_progress`` was never
    # invoked (orchestrator returned without entering any agent) so the
    # row still exists with whatever was compiled at the end.
    trace_row = _upsert_agent_trace_row(db, sess, result.trace_payload, trace_box["row"])

    reporter_payload = result.reporter_summary.model_dump() if result.reporter_summary else None
    return result.bundle, trace_row.id, reporter_payload


# Human-readable copy for ``status_message``. Mirrors the friendly
# labels the frontend uses for the Agent Trace scaffold so the status
# pill and the trace card tell the same story.
_AGENT_RUNNING_LABELS: dict[str, str] = {
    "coordinator": "Coordinator — planning the workflow…",
    "scout": "Scout — choosing the satellite scene…",
    "historian": "Historian — gathering trends and grounded context…",
    "analyst": "Analyst — writing the brief and self-checking it…",
    "reporter": "Reporter — writing the public summary…",
}
_AGENT_DONE_LABELS: dict[str, str] = {
    "coordinator": "Coordinator finished — plan ready",
    "scout": "Scout finished — scene selected",
    "historian": "Historian finished — context briefing ready",
    "analyst": "Analyst finished — narrative drafted",
    "reporter": "Reporter finished — citizen summary ready",
}


def _upsert_agent_trace_row(
    db: DBSession,
    sess: MonitoringSession,
    trace_payload: dict[str, Any],
    existing: AgentTrace | None,
) -> AgentTrace:
    """Insert or update the agent_traces row from a compiled payload.

    Callable many times across a session run — once per agent during
    incremental progress + a final pass at the end. Repeated calls
    mutate the same row so the UI sees the trace fill in live.
    """
    payload_runs = trace_payload.get("agent_runs") or []
    payload_plan = trace_payload.get("coordinator_plan") or {}
    if existing is None:
        existing = db.query(AgentTrace).filter(AgentTrace.session_id == sess.id).one_or_none()

    if existing is None:
        existing = AgentTrace(
            session_id=sess.id,
            coordinator_plan=payload_plan,
            agent_runs=payload_runs,
            total_tokens_in=int(trace_payload.get("total_tokens_in", 0)),
            total_tokens_out=int(trace_payload.get("total_tokens_out", 0)),
            total_latency_ms=int(trace_payload.get("total_latency_ms", 0)),
            gemini_model=str(trace_payload.get("gemini_model", "gemini-2.5-flash")),
        )
        db.add(existing)
    else:
        existing.coordinator_plan = payload_plan or existing.coordinator_plan
        existing.agent_runs = payload_runs
        existing.total_tokens_in = int(trace_payload.get("total_tokens_in", 0))
        existing.total_tokens_out = int(trace_payload.get("total_tokens_out", 0))
        existing.total_latency_ms = int(trace_payload.get("total_latency_ms", 0))
        existing.gemini_model = str(
            trace_payload.get("gemini_model", existing.gemini_model or "gemini-2.5-flash")
        )
    db.commit()
    db.refresh(existing)
    return existing


def run_full(session_id: UUID) -> None:
    """Run every step of the pipeline for one session."""

    with _open_session() as db:
        sess, water_body = _load_session_and_water_body(db, session_id)
        _set_status(db, sess, SessionStatus.PROCESSING, "Fetching imagery")

        try:
            bundle = retrieve_imagery(sess, water_body)
            store_imagery_metadata(db, sess, bundle)
            LOGGER.info("Imagery acquired for session %s: %s", sess.id, bundle.scene_id)

            _set_status(db, sess, SessionStatus.PROCESSING, "Computing indices")
            index_bundle = compute_all(bundle.bands)
            indices = store_indices(db, sess, index_bundle.aggregates)
            _store_aoi_classification(db, sess, index_bundle.water_fraction)
            LOGGER.info(
                "Indices computed for session %s · water_fraction=%.2f aoi=%s",
                sess.id,
                index_bundle.water_fraction,
                sess.aoi_type,
            )

            _set_status(db, sess, SessionStatus.PROCESSING, "Scoring risk")
            risk = score_and_explain(db, sess, water_body, indices)
            LOGGER.info("Risk %s/%s for session %s", risk.level, risk.urgency, sess.id)

            _set_status(db, sess, SessionStatus.PROCESSING, "Generating report")
            evidence = _existing_evidence(db, sess)
            generate_and_store_report(db, sess, water_body, indices, evidence, risk)

            _set_status(db, sess, SessionStatus.COMPLETE, "Report ready")
        except Exception as exc:  # pragma: no cover - exercised via integration
            LOGGER.exception("Pipeline failed for session %s", sess.id)
            _set_status(db, sess, SessionStatus.FAILED, f"{type(exc).__name__}: {exc}")


def rescore_with_new_evidence(session_id: UUID) -> None:
    """Re-run scoring, narrative, and report after new evidence arrives."""
    with _open_session() as db:
        sess, water_body = _load_session_and_water_body(db, session_id)
        indices = db.query(SpectralIndex).filter(SpectralIndex.session_id == sess.id).all()
        if not indices:
            # No imagery yet — kick off the full pipeline instead.
            run_full(session_id)
            return

        _set_status(db, sess, SessionStatus.PROCESSING, "Re-scoring with new evidence")
        risk = score_and_explain(db, sess, water_body, indices)
        evidence = _existing_evidence(db, sess)
        generate_and_store_report(db, sess, water_body, indices, evidence, risk)
        _set_status(db, sess, SessionStatus.COMPLETE, "Updated report ready")
