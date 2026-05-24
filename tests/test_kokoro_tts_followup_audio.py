from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import AUDIO_DIR, DB_PATH, app
from backend.app.db import save_transcript


def test_followup_audio_returns_playable_url(monkeypatch):
    client = TestClient(app)

    create_resp = client.post('/api/debrief/sessions', json={})
    session_id = create_resp.json()['session_id']
    save_transcript(DB_PATH, session_id, 'Need owner for Johnson family follow-up by Friday.', 'manual-test')

    def fake_followup(*, transcript_text: str, memory_facts: list[str], skill_hints: list[str]):
        assert 'Johnson family' in transcript_text
        return {'question': 'Who owns the Johnson family follow-up?', 'model': 'gpt-4.1-mini'}

    def fake_tts(*, text: str):
        assert text == 'Who owns the Johnson family follow-up?'
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        out = AUDIO_DIR / 'fake-followup.wav'
        out.write_bytes(b'RIFFfakeWAVE')
        return out

    monkeypatch.setattr('backend.app.main.generate_followup_question_openai', fake_followup)
    monkeypatch.setattr('backend.app.main.synthesize_kokoro_tts', fake_tts)

    resp = client.post(f'/api/debrief/sessions/{session_id}/follow-up-audio')

    assert resp.status_code == 200
    data = resp.json()
    assert data['session_id'] == session_id
    assert data['follow_up_question'] == 'Who owns the Johnson family follow-up?'
    assert data['llm_model'] == 'gpt-4.1-mini'
    assert data['tts_provider'] == 'kokoro'
    assert data['audio_url'].startswith('/audio/')



def test_followup_audio_without_transcript_returns_400(monkeypatch):
    client = TestClient(app)

    create_resp = client.post('/api/debrief/sessions', json={})
    session_id = create_resp.json()['session_id']

    def fake_followup(*, transcript_text: str, memory_facts: list[str], skill_hints: list[str]):
        return {'question': 'irrelevant', 'model': 'gpt-4.1-mini'}

    monkeypatch.setattr('backend.app.main.generate_followup_question_openai', fake_followup)

    resp = client.post(f'/api/debrief/sessions/{session_id}/follow-up-audio')
    assert resp.status_code == 400
    assert 'no transcript' in resp.json()['detail'].lower()


def test_followup_audio_unknown_session_returns_404():
    client = TestClient(app)
    resp = client.post('/api/debrief/sessions/not-real/follow-up-audio')
    assert resp.status_code == 404
