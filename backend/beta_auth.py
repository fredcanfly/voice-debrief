from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from fastapi import HTTPException

from .config import Settings
from .supabase_gateway import SupabaseGateway


@dataclass
class AuthUser:
    user_id: str
    email: str | None = None


def parse_allowed_emails(raw: str) -> set[str]:
    return {part.strip().lower() for part in raw.split(',') if part.strip()}


def supabase_configured(settings: Settings) -> bool:
    return not settings.supabase_url.startswith('https://YOUR_PROJECT')


async def resolve_auth_user(
    settings: Settings,
    gateway: SupabaseGateway,
    authorization: str | None,
    x_dev_user_id: str | None,
    x_dev_user_email: str | None,
) -> AuthUser:
    if not settings.multi_user_mode:
        return AuthUser(user_id=x_dev_user_id or 'local-bob', email=x_dev_user_email)

    if x_dev_user_id:
        return AuthUser(user_id=x_dev_user_id, email=x_dev_user_email)

    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail='Missing Bearer token')

    token = authorization.split(' ', 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail='Empty Bearer token')

    if not supabase_configured(settings):
        raise HTTPException(status_code=503, detail='Supabase is not configured yet')

    try:
        user_data = await gateway.get_user_from_bearer(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f'Invalid auth token: {exc}') from exc

    return AuthUser(user_id=str(user_data.get('id')), email=user_data.get('email'))


def can_signup(
    *,
    settings: Settings,
    existing_user_ids: Iterable[str],
    email: str | None,
    requesting_user_id: str | None,
) -> tuple[bool, str]:
    existing_set = set(existing_user_ids)
    if requesting_user_id and requesting_user_id in existing_set:
        return True, 'existing-user'

    allowed = parse_allowed_emails(settings.allowed_emails)
    normalized_email = (email or '').strip().lower()

    if allowed and normalized_email not in allowed:
        return False, 'email-not-allowlisted'

    if not settings.beta_signups_open:
        return False, 'signups-closed'

    if len(existing_set) >= int(settings.max_beta_users):
        return False, 'user-cap-reached'

    return True, 'ok'
