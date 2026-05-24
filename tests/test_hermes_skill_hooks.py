from fastapi.testclient import TestClient

from backend.app.db import get_session_skill_hints
from backend.app.main import DB_PATH, app


def test_transcribe_persists_skill_hints(monkeypatch):
    client = TestClient(app)
    session_id = client.post('/api/debrief/sessions', json={}).json()['session_id']

    monkeypatch.setattr(
        'backend.app.main.transcribe_file_openai',
        lambda _path: {'text': 'Johnson family topic is sensitive. Start gently and avoid direct probing.', 'model': 'gpt-4o-mini-transcribe'},
    )
    monkeypatch.setattr(
        'backend.app.main.extract_skill_hints_from_transcript',
        lambda text: ['Sensitive topic handling: start gently', 'Avoid direct probing first'],
    )

    files = {'file': ('turn.webm', b'fake-audio', 'audio/webm')}
    resp = client.post(f'/api/debrief/sessions/{session_id}/transcribe', files=files)
    assert resp.status_code == 200

    hints = get_session_skill_hints(DB_PATH, session_id)
    assert hints == ['Sensitive topic handling: start gently', 'Avoid direct probing first']


def test_followup_reuses_skill_hints(monkeypatch):
    client = TestClient(app)
    session_id = client.post('/api/debrief/sessions', json={}).json()['session_id']

    monkeypatch.setattr(
        'backend.app.main.transcribe_file_openai',
        lambda _path: {'text': 'Johnson family situation remains sensitive and emotional.', 'model': 'gpt-4o-mini-transcribe'},
    )
    monkeypatch.setattr(
        'backend.app.main.extract_skill_hints_from_transcript',
        lambda text: ['Sensitive topic handling: start gently'],
    )

    files = {'file': ('turn.webm', b'fake-audio', 'audio/webm')}
    assert client.post(f'/api/debrief/sessions/{session_id}/transcribe', files=files).status_code == 200

    captured = {}

    def fake_followup(*, transcript_text: str, memory_facts: list[str], skill_hints: list[str]):
        captured['skill_hints'] = skill_hints
        return {'question': 'Anything sensitive to remember before Friday?', 'model': 'gpt-4.1-mini'}

    monkeypatch.setattr('backend.app.main.generate_followup_question_openai', fake_followup)

    resp = client.post(f'/api/debrief/sessions/{session_id}/follow-up-question')
    assert resp.status_code == 200
    assert captured['skill_hints'] == ['Sensitive topic handling: start gently']
