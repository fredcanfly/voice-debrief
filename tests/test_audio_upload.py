from fastapi.testclient import TestClient

from backend.app.main import app


def test_audio_upload_endpoint_saves_file_and_returns_metadata() -> None:
    client = TestClient(app)

    payload = b"RIFF....fake-audio-bytes"
    files = {"file": ("turn.webm", payload, "audio/webm")}

    response = client.post("/api/debrief/audio-upload", files=files)
    assert response.status_code == 200

    data = response.json()
    assert data["upload_id"]
    assert data["filename"].endswith(".webm")
    assert data["bytes_received"] == len(payload)
