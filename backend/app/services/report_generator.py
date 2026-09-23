"""Render an HTML / PDF report for a monitoring session."""

from __future__ import annotations

import base64
from collections.abc import Iterable
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, StrictUndefined
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.evidence import FieldEvidence
from app.models.report import Report
from app.models.risk_assessment import RiskAssessment
from app.models.session import MonitoringSession
from app.models.spectral_index import SpectralIndex
from app.models.water_body import WaterBody
from app.schemas.risk import RiskAssessmentRead
from app.services.citizen_summary import build_citizen_summary
from app.utils.charts import index_bar_svg
from app.utils.location import format_location_label
from app.utils.pdf import render_pdf

LOGGER = get_logger(__name__)

_TEMPLATE_ENV = Environment(undefined=StrictUndefined, autoescape=True)
_TEMPLATE = _TEMPLATE_ENV.from_string(
    files("app.services.templates").joinpath("report.html.j2").read_text(encoding="utf-8")
)


def _load_brand_logo_data_url() -> str | None:
    # Use native vector AquaLinks HTML/SVG header in report.html.j2
    return None


_BRAND_LOGO_DATA_URL = _load_brand_logo_data_url()


def render_report_html(
    *,
    session: MonitoringSession,
    water_body: WaterBody,
    indices: Iterable[SpectralIndex],
    evidence: Iterable[FieldEvidence],
    risk: RiskAssessment,
) -> str:
    """Render the report HTML."""

    indices_rendered = [
        {
            "name": idx.name.value,
            "value": idx.value,
            "bands": idx.bands,
            "interpretation": idx.interpretation,
            "chart_svg": index_bar_svg(idx.name, idx.value),
        }
        for idx in indices
    ]

    evidence_list = list(evidence)
    citizen_summary = build_citizen_summary(
        risk=RiskAssessmentRead.model_validate(risk) if risk else None,
        aoi_type=session.aoi_type,
        water_fraction=session.water_fraction,
        evidence_count=len(evidence_list),
        reporter_payload=risk.field_brief if risk else None,
    )

    return _TEMPLATE.render(
        session=session,
        water_body=water_body,
        location_label=format_location_label(name=water_body.name, centroid=water_body.centroid),
        indices=indices_rendered,
        evidence=evidence_list,
        risk=risk,
        citizen_summary=citizen_summary,
        agent_summary=_summarise_agent_trace(risk),
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        brand_logo_data_url=_BRAND_LOGO_DATA_URL,
    )


_AGENT_STEP_META: dict[str, dict[str, str]] = {
    "coordinator": {
        "label": "Coordinator",
        "subtitle": "Planned the workflow",
    },
    "scout": {
        "label": "Scout",
        "subtitle": "Picked the satellite scene",
    },
    "historian": {
        "label": "Historian",
        "subtitle": "Pulled past observations and outside context",
    },
    "analyst": {
        "label": "Analyst",
        "subtitle": "Wrote the brief and self-checked it",
    },
    "reporter": {
        "label": "Reporter",
        "subtitle": "Wrote the citizen-facing summary card",
    },
    "field_liaison": {
        "label": "Field Liaison",
        "subtitle": "Turned the brief into a field plan (legacy)",
    },
}


def _plain_english_step(agent: str, run: dict[str, object]) -> str:
    """One sentence per agent, in plain language a non-engineer can follow."""
    outputs = run.get("outputs") if isinstance(run.get("outputs"), dict) else {}
    outputs = outputs or {}

    if agent == "coordinator":
        plan = outputs.get("plan") if isinstance(outputs, dict) else None
        if isinstance(plan, list) and plan:
            names = [
                _AGENT_STEP_META.get(str(step.get("agent")), {}).get("label")
                or str(step.get("agent"))
                for step in plan
                if isinstance(step, dict)
            ]
            return (
                "Read the chosen area plus its history and decided which "
                "agents to invoke for this run: " + " → ".join(names) + "."
            )
        return "Read the chosen area and history, then decided which agents to run."

    if agent == "scout":
        scene = outputs.get("selected_scene_id") if isinstance(outputs, dict) else None
        cloud = outputs.get("selected_cloud_cover") if isinstance(outputs, dict) else None
        when = outputs.get("selected_capture_date") if isinstance(outputs, dict) else None
        cloud_str = (
            f" with about {float(cloud):.0f}% cloud cover" if isinstance(cloud, int | float) else ""
        )
        when_str = f" (captured {str(when)[:10]})" if isinstance(when, str) and when else ""
        if scene:
            return (
                f"Chose Sentinel-2 scene {scene}{cloud_str}{when_str}. "
                "If the freshest scene looked hazy over the chosen area, "
                "the Scout asked Gemini Vision to confirm and re-queried with "
                "a tighter cloud bound."
            )
        return "Chose the best Sentinel-2 scene that intersected the chosen area."

    if agent == "historian":
        text = ""
        briefing = outputs.get("briefing_text") if isinstance(outputs, dict) else None
        if isinstance(briefing, str) and briefing.strip():
            text = briefing.strip()
        trend = outputs.get("trend") if isinstance(outputs, dict) else None
        if isinstance(trend, dict) and trend.get("summary"):
            text = (text + " " + str(trend["summary"])).strip()
        return text or (
            "Pulled past sessions, computed a trend, and searched the open web "
            "for relevant local water-quality news."
        )

    if agent == "analyst":
        critique = outputs.get("critique") if isinstance(outputs, dict) else None
        rewrote = bool(outputs.get("rewrote")) if isinstance(outputs, dict) else False
        bundle = outputs.get("bundle") if isinstance(outputs, dict) else None
        reasoning = bundle.get("reasoning") if isinstance(bundle, dict) else None
        text = ""
        if isinstance(reasoning, str) and reasoning.strip():
            # Keep it short for the PDF — first sentence + ellipsis if longer.
            text = reasoning.split(". ")[0].rstrip(".") + "."
        suffix = ""
        if rewrote:
            suffix = (
                " The Critic flagged the first draft, so the Analyst rewrote once "
                "to fix the violations."
            )
        elif isinstance(critique, dict) and critique.get("accept_draft"):
            suffix = " The Critic accepted the first draft without changes."
        return (text or "Drafted the recommendation and reasoning above.") + suffix

    if agent == "reporter":
        headline = outputs.get("headline") if isinstance(outputs, dict) else None
        bottom_line = outputs.get("bottom_line") if isinstance(outputs, dict) else None
        if isinstance(headline, str) and headline.strip():
            suffix = (
                f" {bottom_line}" if isinstance(bottom_line, str) and bottom_line.strip() else ""
            )
            return f"Produced the public summary: {headline}.{suffix}"
        return "Produced the citizen-facing summary card for this run."

    if agent == "field_liaison":
        tasks = outputs.get("tasks") if isinstance(outputs, dict) else None
        n = len(tasks) if isinstance(tasks, list) else 0
        if n:
            word = "task" if n == 1 else "tasks"
            return (
                f"Turned the brief into {n} prioritised field {word} for the "
                "team, with locations, equipment, and photo prompts."
            )
        return "Turned the brief into a prioritised field plan for the team."

    return "Contributed to the run."


def _summarise_agent_trace(risk: RiskAssessment | None) -> dict[str, object] | None:
    """Plain-English agent summary for the PDF.

    Produces a ``steps`` list — one row per agent that ran, with a short
    label, a subtitle, and a one-sentence description of what that agent
    accomplished on this session. Citations from the Historian's
    grounded search are surfaced separately so the field team can
    follow up on real sources.
    """
    if risk is None or risk.agent_trace_id is None:
        return None

    # Avoid a circular import — AgentTrace is heavyweight to import.
    from sqlmodel import Session as SQLModelSession

    from app.core.database import get_engine
    from app.models import AgentTrace

    with SQLModelSession(get_engine()) as db:
        trace = db.get(AgentTrace, risk.agent_trace_id)
        if trace is None:
            return None

        steps: list[dict[str, str]] = []
        citations: list[dict[str, object]] = []
        agents_ran: list[str] = []

        # Coordinator entry is reconstructed from the persisted plan
        # so the PDF shows the planning step even though the
        # orchestrator doesn't always record it as a separate run.
        plan = trace.coordinator_plan or {}
        if plan and (plan.get("plan") or plan.get("rationale")):
            steps.append(
                {
                    "label": _AGENT_STEP_META["coordinator"]["label"],
                    "subtitle": _AGENT_STEP_META["coordinator"]["subtitle"],
                    "body": _plain_english_step("coordinator", {"outputs": plan}),
                }
            )

        for run in trace.agent_runs or []:
            name = run.get("agent") if isinstance(run, dict) else None
            if not isinstance(name, str):
                continue
            agents_ran.append(name)
            meta = _AGENT_STEP_META.get(name)
            if meta is None:
                continue
            steps.append(
                {
                    "label": meta["label"],
                    "subtitle": meta["subtitle"],
                    "body": _plain_english_step(name, run),
                }
            )
            extras = (run.get("outputs") or {}).get("extras") or {}
            for c in extras.get("citations") or []:
                if isinstance(c, dict):
                    citations.append(c)

        return {
            "agents_ran": agents_ran,
            "steps": steps,
            "total_tokens": trace.total_tokens_in + trace.total_tokens_out,
            "total_latency_ms": trace.total_latency_ms,
            "gemini_model": trace.gemini_model,
            "citations": citations,
        }


def render_report_pdf(html: str) -> bytes:
    return render_pdf(html)


def persist_report(
    db: Session,
    *,
    session: MonitoringSession,
    pdf_bytes: bytes,
) -> Report:
    """Write the PDF to disk and upsert the ``Report`` row."""

    settings = get_settings()
    settings.report_dir.mkdir(parents=True, exist_ok=True)
    target: Path = settings.report_dir / f"{session.id}.pdf"
    target.write_bytes(pdf_bytes)

    existing = db.query(Report).filter(Report.session_id == session.id).one_or_none()
    if existing is None:
        existing = Report(
            session_id=session.id,
            file_path=str(target),
            byte_size=len(pdf_bytes),
        )
        db.add(existing)
    else:
        existing.file_path = str(target)
        existing.byte_size = len(pdf_bytes)
    db.commit()
    db.refresh(existing)
    return existing
