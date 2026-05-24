import sqlite3

from fastapi.testclient import TestClient

from backend.app.main import DB_PATH, app


def test_session_transcribe_uses_openai_and_saves_transcript(monkeypatch):
    client = TestClient(app)

    create_resp = client.post('/api/debrief/sessions', json={})
    session_id = create_resp.json()['session_id']

    def fake_transcribe(_path):
        return {'text': 'Met with Johnson family about follow-up.', 'model': 'gpt-4o-mini-transcribe'}

    monkeypatch.setattr('backend.app.main.transcribe_file_openai', fake_transcribe)

    payload = b'fake-webm-audio'
    files = {'file': ('turn.webm', payload, 'audio/webm')}
    resp = client.post(f'/api/debrief/sessions/{session_id}/transcribe', files=files)

    assert resp.status_code == 200
    data = resp.json()
    assert data['session_id'] == session_id
    assert data['transcript_text'] == 'Met with Johnson family about follow-up.'
    assert data['stt_model'] == 'gpt-4o-mini-transcribe'

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT transcript_text, stt_model FROM debrief_transcripts WHERE session_id=? ORDER BY id DESC LIMIT 1",
            (session_id,),
        ).fetchone()

    assert row is not None
    assert row[0] == 'Met with Johnson family about follow-up.'


def test_session_transcribe_unknown_session_returns_404():
    client = TestClient(app)
    payload = b'fake-webm-audio'
    files = {'file': ('turn.webm', payload, 'audio/webm')}
    resp = client.post('/api/debrief/sessions/not-real/transcribe', files=files)
    assert resp.status_code == 404
