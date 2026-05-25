from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app


def test_admin_feedback_ingestion_appends_csv(monkeypatch, tmp_path):
    client = TestClient(app)

    log_path = tmp_path / 'feedback_log.csv'
    log_path.write_text(
        'timestamp_utc,user_id,trust_score,cognitive_load_score,notes,next_changes\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('FEEDBACK_LOG_PATH', str(log_path))
    monkeypatch.setenv('ADMIN_API_KEY', 'pilot-admin-key')

    resp = client.post(
        '/api/admin/feedback-entry',
        headers={'x-admin-key': 'pilot-admin-key'},
        json={
            'user_id': 'pilot-01',
            'trust_score': 4,
            'cognitive_load_score': 5,
            'notes': 'Helpful and fast',
            'next_changes': 'Shorter follow-up tone',
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body['ok'] is True

    rows = log_path.read_text(encoding='utf-8').strip().splitlines()
    assert len(rows) == 2
    assert 'pilot-01,4,5,Helpful and fast,Shorter follow-up tone' in rows[1]
