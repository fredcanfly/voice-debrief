from uuid import uuid4

from fastapi.testclient import TestClient

import backend.app.main as main_mod
from backend.app.db import save_transcript
from backend.app.main import DB_PATH, app


def test_telegram_link_status_flow() -> None:
    client = TestClient(app)
    user_id = f"tg-user-{uuid4().hex[:8]}"

    empty = client.get('/api/integrations/telegram/status', headers={'x-user-id': user_id})
    assert empty.status_code == 200
    assert empty.json()['linked'] is False

    linked = client.post(
        '/api/integrations/telegram/link',
        headers={'x-user-id': user_id},
        json={'telegram_chat_id': '6410460559'},
    )
    assert linked.status_code == 200
    assert linked.json()['linked'] is True

    after = client.get('/api/integrations/telegram/status', headers={'x-user-id': user_id})
    assert after.status_code == 200
    assert after.json()['linked'] is True


def test_generate_document_autosends_when_telegram_linked(monkeypatch) -> None:
    client = TestClient(app)
    user_id = f"tg-send-{uuid4().hex[:8]}"

    created = client.post('/api/debrief/sessions', headers={'x-user-id': user_id}, json={})
    assert created.status_code == 200
    session_id = created.json()['session_id']

    save_transcript(DB_PATH, session_id, 'I had a productive meeting and next actions.', 'test-model')

    client.post(
        '/api/integrations/telegram/link',
        headers={'x-user-id': user_id},
        json={'telegram_chat_id': '6410460559'},
    )

    monkeypatch.setattr(
        main_mod,
        'generate_debrief_document_openai',
        lambda transcript_text: {
            'title': 'Test Debrief',
            'slug': 'test-debrief',
            'model': 'fake-model',
            'markdown': '# Debrief\n\nThis is a generated test debrief.',
        },
    )

    sent = {'count': 0, 'last_chat_id': None, 'last_text': ''}

    def fake_send(chat_id: str, text: str) -> bool:
        sent['count'] += 1
        sent['last_chat_id'] = chat_id
        sent['last_text'] = text
        return True

    monkeypatch.setattr(main_mod, '_send_telegram_note', fake_send)

    resp = client.post(
        f'/api/debrief/sessions/{session_id}/generate-document',
        headers={'x-user-id': user_id},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body['title'] == 'Test Debrief'
    assert sent['count'] == 1
    assert sent['last_chat_id'] == '6410460559'
    assert session_id in sent['last_text']
