from fastapi.testclient import TestClient

from backend.app.main import app


def test_session_is_scoped_to_owner_user_id():
    client = TestClient(app)

    create = client.post('/api/debrief/sessions', json={}, headers={'x-user-id': 'user-a'})
    assert create.status_code == 200
    session_id = create.json()['session_id']

    owner_resp = client.post(
        f'/api/debrief/sessions/{session_id}/start',
        headers={'x-user-id': 'user-a'},
    )
    assert owner_resp.status_code == 200

    other_resp = client.post(
        f'/api/debrief/sessions/{session_id}/start',
        headers={'x-user-id': 'user-b'},
    )
    assert other_resp.status_code == 403
    assert 'not your session' in other_resp.json()['detail'].lower()


def test_missing_user_header_defaults_to_local_user_for_backwards_compatibility():
    client = TestClient(app)

    create = client.post('/api/debrief/sessions', json={})
    assert create.status_code == 200
    session_id = create.json()['session_id']

    ok = client.post(f'/api/debrief/sessions/{session_id}/start')
    assert ok.status_code == 200

    denied = client.post(
        f'/api/debrief/sessions/{session_id}/start',
        headers={'x-user-id': 'other-user'},
    )
    assert denied.status_code == 403
