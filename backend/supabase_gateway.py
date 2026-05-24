from __future__ import annotations

import httpx


class SupabaseGateway:
    def __init__(self, *, url: str, anon_key: str, service_role_key: str):
        self.url = url.rstrip('/')
        self.anon_key = anon_key
        self.service_role_key = service_role_key

    async def get_user_from_bearer(self, bearer_token: str) -> dict:
        headers = {
            'apikey': self.anon_key,
            'Authorization': f'Bearer {bearer_token}',
        }
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(f'{self.url}/auth/v1/user', headers=headers)
        if res.status_code >= 400:
            raise ValueError(f'Invalid token: {res.text}')
        return res.json()

    async def count_profiles(self) -> int:
        headers = {
            'apikey': self.service_role_key,
            'Authorization': f'Bearer {self.service_role_key}',
            'Prefer': 'count=exact',
        }
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(f'{self.url}/rest/v1/profiles?select=id', headers=headers)
        res.raise_for_status()
        content_range = res.headers.get('content-range', '0-0/0')
        try:
            return int(content_range.split('/')[-1])
        except Exception:
            return len(res.json())

    async def ensure_profile(self, *, user_id: str, email: str | None) -> None:
        headers = {
            'apikey': self.service_role_key,
            'Authorization': f'Bearer {self.service_role_key}',
            'Content-Type': 'application/json',
            'Prefer': 'resolution=merge-duplicates,return=minimal',
        }
        payload = {'id': user_id, 'email': email}
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(f'{self.url}/rest/v1/profiles', headers=headers, json=payload)
        res.raise_for_status()

    async def get_user_settings(self, *, user_id: str) -> dict | None:
        headers = {
            'apikey': self.service_role_key,
            'Authorization': f'Bearer {self.service_role_key}',
        }
        params = {'select': '*', 'user_id': f'eq.{user_id}', 'limit': '1'}
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(f'{self.url}/rest/v1/user_settings', headers=headers, params=params)
        res.raise_for_status()
        rows = res.json()
        return rows[0] if rows else None

    async def upsert_user_settings(self, *, user_id: str, settings_payload: dict) -> dict:
        headers = {
            'apikey': self.service_role_key,
            'Authorization': f'Bearer {self.service_role_key}',
            'Content-Type': 'application/json',
            'Prefer': 'resolution=merge-duplicates,return=representation',
        }
        payload = {'user_id': user_id, **settings_payload}
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(f'{self.url}/rest/v1/user_settings', headers=headers, json=payload)
        res.raise_for_status()
        rows = res.json()
        return rows[0] if rows else payload
