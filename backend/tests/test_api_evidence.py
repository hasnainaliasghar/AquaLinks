"""API tests for the evidence and report endpoints."""

from __future__ import annotations

import re
import time
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image


def _create_session(client: TestClient, polygon: dict) -> str:
    response = client.post(
        "/api/v1/sessions",
        json={
            "new_water_body": {"name": "Evidence Lake", "geometry": polygon},
            "max_cloud_cover": 30,
        },
    )
    assert response.status_code == 201
    sid = response.json()["id"]
    for _ in range(30):
        if client.get(f"/api/v1/sessions/{sid}").json()["status"] == "complete":
            return sid
        time.sleep(0.1)
    raise AssertionError("session did not complete")


def _photo_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (32, 32), (10, 90, 120)).save(buf, format="JPEG")
    return buf.getvalue()


def test_submit_evidence_updates_risk(client: TestClient, sample_polygon):
    sid = _create_session(client, sample_polygon)
    baseline = client.get(f"/api/v1/sessions/{sid}").json()
    baseline_score = baseline["risk"]["score"]

    files = {"photo": ("photo.jpg", _photo_bytes(), "image/jpeg")}
    data = {
        "payload": (
            '{"water_color": "green", "odor": "rotten", "algae_present": true, '
            '"dead_fish_count": 6, "rainfall_mm": 20.0, "complaints_count": 3}'
        )
    }
    submit = client.post(f"/api/v1/sessions/{sid}/evidence", data=data, files=files)
    assert submit.status_code == 201
    assert submit.json()["photo_url"]

    # Rescoring happens via BackgroundTasks; poll briefly.
    for _ in range(30):
        detail = client.get(f"/api/v1/sessions/{sid}").json()
        if detail["status"] == "complete" and detail["risk"]["score"] != baseline_score:
            break
        time.sleep(0.1)
    assert detail["risk"]["score"] >= baseline_score


def test_report_download_returns_pdf(client: TestClient, sample_polygon):
    sid = _create_session(client, sample_polygon)
    response = client.get(f"/api/v1/sessions/{sid}/report")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    content_disposition = response.headers.get("content-disposition", "")
    assert re.search(r'filename="aqualens-analysis-\d{8}\.pdf"', content_disposition)
    assert response.content.startswith(b"%PDF")
