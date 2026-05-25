from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app


def test_admin_weekly_usage_report_endpoint_writes_file(monkeypatch, tmp_path):
    client = TestClient(app)
    monkeypatch.setenv('ADMIN_API_KEY', 'pilot-admin-key')

    out_file = tmp_path / 'weekly_usage.md'
    resp = client.post(
        '/api/admin/weekly-usage-report',
        headers={'x-admin-key': 'pilot-admin-key'},
        json={'output_path': str(out_file)},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body['ok'] is True
    assert Path(body['output_path']).exists()

    text = Path(body['output_path']).read_text(encoding='utf-8')
    assert '# Weekly Usage Summary' in text
    assert 'session_created' in text
