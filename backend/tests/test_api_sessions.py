"""API tests for water bodies and monitoring sessions."""

from __future__ import annotations

import time
from uuid import uuid4

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_water_body_and_session(client: TestClient, sample_polygon):
    payload = {
        "name": "API Lake",
        "geometry": sample_polygon,
        "description": "Pytest fixture",
    }
    wb_response = client.post("/api/v1/water-bodies", json=payload)
    assert wb_response.status_code == 201
    wb = wb_response.json()
    assert wb["name"] == "API Lake"
    assert wb["area_km2"] > 0

    session_response = client.post(
        "/api/v1/sessions",
        json={"water_body_id": wb["id"], "max_cloud_cover": 40},
    )
    assert session_response.status_code == 201
    session = session_response.json()
    assert session["water_body"]["id"] == wb["id"]

    # BackgroundTasks runs synchronously inside TestClient lifespan; the
    # status should reach `complete` after a tiny grace period.
    for _ in range(20):
        detail = client.get(f"/api/v1/sessions/{session['id']}").json()
        if detail["status"] == "complete":
            break
        time.sleep(0.1)
    else:
        raise AssertionError("session did not complete")

    assert len(detail["indices"]) == 6
    assert detail["risk"] is not None
    assert detail["risk"]["recommendation"]


def test_create_session_with_new_water_body_inline(client: TestClient, sample_polygon):
    response = client.post(
        "/api/v1/sessions",
        json={
            "new_water_body": {
                "name": "Inline Lake",
                "geometry": sample_polygon,
                "source": "user_drawn",
            },
            "max_cloud_cover": 30,
        },
    )
    assert response.status_code == 201
    assert response.json()["water_body"]["name"] == "Inline Lake"


def test_list_sessions_returns_created_session(client: TestClient, sample_polygon):
    client.post(
        "/api/v1/sessions",
        json={
            "new_water_body": {
                "name": "List Lake",
                "geometry": sample_polygon,
            },
        },
    )
    response = client.get("/api/v1/sessions")
    assert response.status_code == 200
    body = response.json()
    assert any(item["water_body_name"] == "List Lake" for item in body)


def test_bulk_delete_water_bodies_removes_selected_rows(client: TestClient, sample_polygon):
    created_ids: list[str] = []
    for i in range(2):
        resp = client.post(
            "/api/v1/water-bodies",
            json={
                "name": f"Bulk Lake {i}",
                "geometry": sample_polygon,
            },
        )
        assert resp.status_code == 201
        created_ids.append(resp.json()["id"])

    bulk = client.post("/api/v1/water-bodies/bulk-delete", json={"ids": created_ids})
    assert bulk.status_code == 200
    assert bulk.json() == {"requested_count": 2, "deleted_count": 2}

    for wb_id in created_ids:
        missing = client.get(f"/api/v1/water-bodies/{wb_id}")
        assert missing.status_code == 404


def test_bulk_delete_is_all_or_nothing_when_any_id_is_missing(client: TestClient, sample_polygon):
    resp = client.post(
        "/api/v1/water-bodies",
        json={"name": "AllOrNothing Lake", "geometry": sample_polygon},
    )
    assert resp.status_code == 201
    wb_id = resp.json()["id"]
    missing_id = str(uuid4())

    bulk = client.post("/api/v1/water-bodies/bulk-delete", json={"ids": [wb_id, missing_id]})
    assert bulk.status_code == 404
    detail = bulk.json()["detail"]
    assert detail["missing_ids"] == [missing_id]

    # The existing row must remain because the operation is transactional.
    still_there = client.get(f"/api/v1/water-bodies/{wb_id}")
    assert still_there.status_code == 200
