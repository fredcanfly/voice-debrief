from fastapi.testclient import TestClient

from backend.app.main import app


def test_pwa_includes_download_button() -> None:
    client = TestClient(app)
    response = client.get('/')

    assert response.status_code == 200
    assert 'Download Latest Debrief' in response.text
