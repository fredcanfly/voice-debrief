from fastapi.testclient import TestClient

from backend.app.db import get_session_memory_facts
from backend.app.main import DB_PATH, app


def test_transcribe_persists_memory_facts(monkeypatch):
    client = TestClient(app)
    session_id = client.post('/api/debrief/sessions', json={}).json()['session_id']

    monkeypatch.setattr(
        'backend.app.main.transcribe_file_openai',
        lambda _path: {'text': 'Johnson family follow-up. Prefers text updates.', 'model': 'gpt-4o-mini-transcribe'},
    )
    monkeypatch.setattr(
        'backend.app.main.extract_memory_facts_from_transcript',
        lambda text: ['Client: Johnson family', 'Preference: text updates'],
    )

    files = {'file': ('turn.webm', b'fake-audio', 'audio/webm')}
    resp = client.post(f'/api/debrief/sessions/{session_id}/transcribe', files=files)
    assert resp.status_code == 200

    facts = get_session_memory_facts(DB_PATH, session_id)
    assert facts == ['Client: Johnson family', 'Preference: text updates']


def test_followup_reuses_persisted_memory_facts(monkeypatch):
    client = TestClient(app)
    session_id = client.post('/api/debrief/sessions', json={}).json()['session_id']

    monkeypatch.setattr(
        'backend.app.main.transcribe_file_openai',
        lambda _path: {'text': 'Discussed Johnson family handoff by Friday.', 'model': 'gpt-4o-mini-transcribe'},
    )
    monkeypatch.setattr(
        'backend.app.main.extract_memory_facts_from_transcript',
        lambda text: ['Client: Johnson family'],
    )

    files = {'file': ('turn.webm', b'fake-audio', 'audio/webm')}
    assert client.post(f'/api/debrief/sessions/{session_id}/transcribe', files=files).status_code == 200

    captured = {}

    def fake_followup(*, transcript_text: str, memory_facts: list[str]):
        captured['memory_facts'] = memory_facts
        return {'question': 'Who owns the Friday handoff?', 'model': 'gpt-4.1-mini'}

    monkeypatch.setattr('backend.app.main.generate_followup_question_openai', fake_followup)

    resp = client.post(f'/api/debrief/sessions/{session_id}/follow-up-question')
    assert resp.status_code == 200
    assert captured['memory_facts'] == ['Client: Johnson family']
