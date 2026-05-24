from fastapi.testclient import TestClient

from backend.app.main import app


def test_pwa_shell_served_from_fastapi_root() -> None:
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Voice Debrief Assistant" in response.text
