from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app


def test_admin_generates_trust_backlog_from_feedback(monkeypatch, tmp_path):
    client = TestClient(app)
    monkeypatch.setenv('ADMIN_API_KEY', 'pilot-admin-key')

    feedback_log = tmp_path / 'feedback_log.csv'
    feedback_log.write_text(
        'timestamp_utc,user_id,trust_score,cognitive_load_score,notes,next_changes\n'
        '2026-05-25T00:00:00Z,pilot-01,2,3,Missed one action item,Improve transcript confidence\n'
        '2026-05-25T00:10:00Z,pilot-02,3,4,Follow-up was too long,Shorten follow-up prompt\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('FEEDBACK_LOG_PATH', str(feedback_log))

    out_path = tmp_path / 'trust_backlog.md'
    resp = client.post(
        '/api/admin/generate-trust-backlog',
        headers={'x-admin-key': 'pilot-admin-key'},
        json={'output_path': str(out_path)},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body['ok'] is True
    assert Path(body['output_path']).exists()

    text = Path(body['output_path']).read_text(encoding='utf-8')
    assert '# Trust Backlog (Auto-generated)' in text
    assert 'Improve transcript confidence' in text
    assert 'Shorten follow-up prompt' in text
