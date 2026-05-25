from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app


def test_admin_pilot_snapshot_combines_usage_and_feedback(monkeypatch, tmp_path):
    client = TestClient(app)
    monkeypatch.setenv('ADMIN_API_KEY', 'pilot-admin-key')

    feedback_log = tmp_path / 'feedback_log.csv'
    feedback_log.write_text(
        'timestamp_utc,user_id,trust_score,cognitive_load_score,notes,next_changes\n'
        '2026-05-25T00:00:00Z,pilot-01,4,5,Helpful,Shorter prompts\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('FEEDBACK_LOG_PATH', str(feedback_log))

    resp = client.get('/api/admin/pilot-snapshot', headers={'x-admin-key': 'pilot-admin-key'})
    assert resp.status_code == 200

    body = resp.json()
    assert 'usage_totals' in body
    assert 'recent_feedback' in body
    assert len(body['recent_feedback']) == 1
    assert body['recent_feedback'][0]['user_id'] == 'pilot-01'
    assert body['recent_feedback'][0]['trust_score'] == 4
