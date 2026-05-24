from fastapi.testclient import TestClient

from backend.app.main import app


def test_create_start_end_session_flow() -> None:
    client = TestClient(app)

    create_resp = client.post("/api/debrief/sessions", json={})
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["status"] == "created"
    assert created["session_id"].startswith("debrief-")

    session_id = created["session_id"]

    start_resp = client.post(f"/api/debrief/sessions/{session_id}/start")
    assert start_resp.status_code == 200
    started = start_resp.json()
    assert started["session_id"] == session_id
    assert started["status"] == "started"
    assert started["started_at"] is not None

    end_resp = client.post(f"/api/debrief/sessions/{session_id}/end")
    assert end_resp.status_code == 200
    ended = end_resp.json()
    assert ended["session_id"] == session_id
    assert ended["status"] == "ended"
    assert ended["ended_at"] is not None


def test_start_unknown_session_returns_404() -> None:
    client = TestClient(app)
    response = client.post("/api/debrief/sessions/not-real/start")
    assert response.status_code == 404
