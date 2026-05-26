from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app


def test_signup_login_me_flow() -> None:
    client = TestClient(app)
    user_id = f"user-{uuid4().hex[:8]}"
    password = "test-pass-123"

    signup_resp = client.post('/api/auth/signup', json={'user_id': user_id, 'password': password})
    assert signup_resp.status_code == 200
    assert signup_resp.json()['ok'] is True

    login_resp = client.post('/api/auth/login', json={'user_id': user_id, 'password': password})
    assert login_resp.status_code == 200
    assert login_resp.json()['user_id'] == user_id

    me_resp = client.get('/api/auth/me', headers={'x-user-id': user_id})
    assert me_resp.status_code == 200
    assert me_resp.json()['user_id'] == user_id


def test_login_rejects_bad_password() -> None:
    client = TestClient(app)
    user_id = f"user-{uuid4().hex[:8]}"

    client.post('/api/auth/signup', json={'user_id': user_id, 'password': 'test-pass-123'})
    bad_login = client.post('/api/auth/login', json={'user_id': user_id, 'password': 'wrong-pass'})

    assert bad_login.status_code == 401
