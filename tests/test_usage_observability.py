from fastapi.testclient import TestClient

from backend.app.main import app


def test_usage_summary_counts_events_for_admin(monkeypatch):
    client = TestClient(app)

    create = client.post('/api/debrief/sessions', json={}, headers={'x-user-id': 'obs-user'})
    session_id = create.json()['session_id']

    monkeypatch.setattr(
        'backend.app.main.transcribe_file_openai',
        lambda _path: {'text': 'Quick debrief turn', 'model': 'gpt-4o-mini-transcribe'},
    )
    files = {'file': ('turn.webm', b'fake-audio', 'audio/webm')}
    tr = client.post(f'/api/debrief/sessions/{session_id}/transcribe', files=files, headers={'x-user-id': 'obs-user'})
    assert tr.status_code == 200

    summary = client.get('/api/admin/usage-summary', headers={'x-admin-key': 'dev-admin-key'})
    assert summary.status_code == 200
    data = summary.json()
    assert data['totals']['session_created'] >= 1
    assert data['totals']['transcribe'] >= 1


def test_usage_summary_requires_admin_key():
    client = TestClient(app)
    denied = client.get('/api/admin/usage-summary')
    assert denied.status_code == 401
