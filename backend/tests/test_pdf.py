"""Smoke test for PDF rendering."""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.evidence import FieldEvidence, Odor, WaterColor
from app.models.risk_assessment import RiskAssessment, RiskLevel, Urgency
from app.models.session import MonitoringSession, SessionStatus
from app.models.spectral_index import IndexName, SpectralIndex
from app.models.water_body import WaterBody
from app.services.report_generator import render_report_html, render_report_pdf


def _fixtures():
    wb = WaterBody(
        name="Renderer Lake",
        description="Used by the PDF smoke test",
        geometry={
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        },
        centroid={"type": "Point", "coordinates": [0.5, 0.5]},
        area_km2=8.3,
        source="test",
    )
    sess = MonitoringSession(
        water_body_id=wb.id,
        start_date=datetime.now(UTC).date(),
        end_date=datetime.now(UTC).date(),
        max_cloud_cover=25.0,
        status=SessionStatus.COMPLETE,
        scene_id="S2A-TEST",
        scene_capture_date=datetime.now(UTC),
        scene_cloud_cover=12.4,
        scene_provider="aqualens-sample",
    )
    indices = [
        SpectralIndex(
            session_id=sess.id,
            name=name,
            value=0.21,
            min_value=-0.1,
            max_value=0.5,
            stddev=0.05,
            interpretation="elevated chlorophyll",
            bands=["B05", "B04"],
            sample_count=120,
        )
        for name in IndexName
    ]
    risk = RiskAssessment(
        session_id=sess.id,
        score=0.61,
        level=RiskLevel.MEDIUM,
        urgency=Urgency.ELEVATED,
        recommendation="Send a sampling team within seven days.",
        reasoning="NDCI and NDTI are both elevated; field evidence reinforces a bloom-onset hypothesis.",
        limitations="Advisory only — confirm with laboratory testing.",
        contributors={"ndci": 0.18, "ndti": 0.12},
    )
    evidence = [
        FieldEvidence(
            session_id=sess.id,
            water_color=WaterColor.GREEN,
            odor=Odor.MUSTY,
            algae_present=True,
            dead_fish_count=2,
            rainfall_mm=4.5,
            complaints_count=1,
            notes="Visible scum along the north shore at 09:30.",
        )
    ]
    return wb, sess, indices, evidence, risk


def test_render_html_contains_risk_level():
    wb, sess, indices, evidence, risk = _fixtures()
    html = render_report_html(
        session=sess, water_body=wb, indices=indices, evidence=evidence, risk=risk
    )
    assert "MEDIUM" in html
    assert "Send a sampling team" in html
    assert "Sentinel-2" in html


def test_render_pdf_returns_pdf_bytes():
    wb, sess, indices, evidence, risk = _fixtures()
    html = render_report_html(
        session=sess, water_body=wb, indices=indices, evidence=evidence, risk=risk
    )
    pdf = render_report_pdf(html)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 5_000
