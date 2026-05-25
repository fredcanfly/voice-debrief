from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app


def test_generate_document_writes_to_user_scoped_directory(monkeypatch):
    client = TestClient(app)

    create = client.post('/api/debrief/sessions', json={}, headers={'x-user-id': 'user-scope'})
    session_id = create.json()['session_id']

    monkeypatch.setattr(
        'backend.app.main.transcribe_file_openai',
        lambda _path: {'text': 'Met Johnson family. Need Friday owner.', 'model': 'gpt-4o-mini-transcribe'},
    )
    files = {'file': ('turn.webm', b'fake-audio', 'audio/webm')}
    tr = client.post(f'/api/debrief/sessions/{session_id}/transcribe', files=files, headers={'x-user-id': 'user-scope'})
    assert tr.status_code == 200

    monkeypatch.setattr(
        'backend.app.main.generate_debrief_document_openai',
        lambda transcript_text: {
            'title': 'Johnson Follow-up',
            'slug': 'johnson-followup',
            'model': 'gpt-4.1-mini',
            'markdown': '# Debrief\n\n- Owner: TBD',
        },
    )

    resp = client.post(
        f'/api/debrief/sessions/{session_id}/generate-document',
        headers={'x-user-id': 'user-scope'},
    )
    assert resp.status_code == 200

    data = resp.json()
    file_path = Path(data['file_path'])
    assert 'generated_docs' in file_path.parts
    assert 'user-scope' in file_path.parts
    assert file_path.exists()
