from fastapi.testclient import TestClient

from backend.app.main import DB_PATH, app
from backend.app.db import save_transcript


def test_document_download_returns_markdown_attachment(monkeypatch):
    client = TestClient(app)
    session_id = client.post('/api/debrief/sessions', json={}).json()['session_id']
    save_transcript(DB_PATH, session_id, 'Transcript for download test.', 'manual')

    def fake_generate(*, transcript_text: str):
        return {
            'markdown': 'Title: Download Test\n\nExecutive summary:\n- item',
            'model': 'gpt-4.1-mini',
            'title': 'Download Test',
            'slug': 'download-test',
        }

    monkeypatch.setattr('backend.app.main.generate_debrief_document_openai', fake_generate)

    gen_resp = client.post(f'/api/debrief/sessions/{session_id}/generate-document')
    assert gen_resp.status_code == 200

    dl_resp = client.get(f'/api/debrief/sessions/{session_id}/document-download')
    assert dl_resp.status_code == 200
    assert 'text/markdown' in dl_resp.headers['content-type']
    assert 'attachment' in dl_resp.headers.get('content-disposition', '').lower()
    assert 'Executive summary' in dl_resp.text


def test_document_download_without_generated_doc_returns_404():
    client = TestClient(app)
    session_id = client.post('/api/debrief/sessions', json={}).json()['session_id']
    dl_resp = client.get(f'/api/debrief/sessions/{session_id}/document-download')
    assert dl_resp.status_code == 404
