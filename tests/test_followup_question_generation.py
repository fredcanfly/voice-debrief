from fastapi.testclient import TestClient

from backend.app.main import app


def test_followup_question_from_latest_transcript(monkeypatch):
    client = TestClient(app)

    session_resp = client.post('/api/debrief/sessions', json={})
    session_id = session_resp.json()['session_id']

    files = {'file': ('turn.webm', b'fake-audio', 'audio/webm')}

    def fake_transcribe(_path):
        return {
            'text': 'Met with Johnson family. Need ownership for counseling follow-up by Friday.',
            'model': 'gpt-4o-mini-transcribe',
        }

    monkeypatch.setattr('backend.app.main.transcribe_file_openai', fake_transcribe)
    transcribe_resp = client.post(f'/api/debrief/sessions/{session_id}/transcribe', files=files)
    assert transcribe_resp.status_code == 200

    def fake_followup(*, transcript_text: str, memory_facts: list[str], skill_hints: list[str]):
        assert 'Johnson family' in transcript_text
        assert isinstance(memory_facts, list)
        assert isinstance(skill_hints, list)
        return {'question': 'Who owns the counseling follow-up by Friday?', 'model': 'gpt-4.1-mini'}

    monkeypatch.setattr('backend.app.main.generate_followup_question_openai', fake_followup)
    resp = client.post(f'/api/debrief/sessions/{session_id}/follow-up-question')

    assert resp.status_code == 200
    data = resp.json()
    assert data['session_id'] == session_id
    assert data['follow_up_question'] == 'Who owns the counseling follow-up by Friday?'
    assert data['llm_model'] == 'gpt-4.1-mini'


def test_followup_question_unknown_session_returns_404():
    client = TestClient(app)
    resp = client.post('/api/debrief/sessions/not-real/follow-up-question')
    assert resp.status_code == 404


def test_followup_question_requires_transcript(monkeypatch):
    client = TestClient(app)
    session_resp = client.post('/api/debrief/sessions', json={})
    session_id = session_resp.json()['session_id']

    def fake_followup(*, transcript_text: str, memory_facts: list[str], skill_hints: list[str]):
        return {'question': 'irrelevant', 'model': 'gpt-4.1-mini'}

    monkeypatch.setattr('backend.app.main.generate_followup_question_openai', fake_followup)
    resp = client.post(f'/api/debrief/sessions/{session_id}/follow-up-question')
    assert resp.status_code == 400
    assert 'no transcript' in resp.json()['detail'].lower()
