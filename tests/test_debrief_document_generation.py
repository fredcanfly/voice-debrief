from fastapi.testclient import TestClient

from backend.app.main import DB_PATH, GENERATED_DOCS_DIR, app
from backend.app.db import save_transcript


def test_generate_debrief_document_returns_markdown_and_saves_file(monkeypatch):
    client = TestClient(app)
    session_id = client.post('/api/debrief/sessions', json={}).json()['session_id']

    save_transcript(DB_PATH, session_id, 'Met with Johnson family about counseling handoff.', 'stt-1')
    save_transcript(DB_PATH, session_id, 'Need owner and Friday deadline confirmation.', 'stt-1')

    def fake_generate(*, transcript_text: str):
        assert 'Johnson family' in transcript_text
        return {
            'markdown': '# Johnson Follow-up Debrief\n\n## Summary\n- Good meeting\n',
            'model': 'gpt-4.1-mini',
            'title': 'Johnson Follow-up Debrief',
            'slug': 'johnson-follow-up-debrief',
        }

    monkeypatch.setattr('backend.app.main.generate_debrief_document_openai', fake_generate)

    resp = client.post(f'/api/debrief/sessions/{session_id}/generate-document')
    assert resp.status_code == 200
    data = resp.json()

    assert data['session_id'] == session_id
    assert data['llm_model'] == 'gpt-4.1-mini'
    assert data['title'] == 'Johnson Follow-up Debrief'
    assert data['file_path'].startswith(str(GENERATED_DOCS_DIR))
    assert '## Summary' in data['markdown']


def test_generate_debrief_document_requires_transcript(monkeypatch):
    client = TestClient(app)
    session_id = client.post('/api/debrief/sessions', json={}).json()['session_id']

    def fake_generate(*, transcript_text: str):
        return {'markdown': 'x', 'model': 'gpt-4.1-mini', 'title': 'x'}

    monkeypatch.setattr('backend.app.main.generate_debrief_document_openai', fake_generate)

    resp = client.post(f'/api/debrief/sessions/{session_id}/generate-document')
    assert resp.status_code == 400
    assert 'no transcript' in resp.json()['detail'].lower()


def test_generate_debrief_document_unknown_session_returns_404():
    client = TestClient(app)
    resp = client.post('/api/debrief/sessions/not-real/generate-document')
    assert resp.status_code == 404
