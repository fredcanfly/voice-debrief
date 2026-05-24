from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from fastapi import Header, HTTPException

from .config import Settings


@dataclass
class AuthUser:
    user_id: str
    email: str | None = None


def parse_allowed_emails(raw: str) -> set[str]:
    return {part.strip().lower() for part in raw.split(',') if part.strip()}


def auth_user_from_headers(
    settings: Settings,
    authorization: str | None,
    x_dev_user_id: str | None,
    x_dev_user_email: str | None,
) -> AuthUser:
    """Scaffolding auth path.

    - local mode: accepts optional X-Dev-User-Id header and defaults to 'local-bob'.
    - multi-user mode: requires Bearer token OR dev header override while Supabase is not wired yet.
    """
    if not settings.multi_user_mode:
        return AuthUser(user_id=x_dev_user_id or 'local-bob', email=x_dev_user_email)

    # Temporary scaffolding path before JWT verification is wired.
    if x_dev_user_id:
        return AuthUser(user_id=x_dev_user_id, email=x_dev_user_email)

    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail='Missing Bearer token')

    token = authorization.split(' ', 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail='Empty Bearer token')

    if settings.supabase_url.startswith('https://YOUR_PROJECT'):
        raise HTTPException(
            status_code=503,
            detail='Supabase is not configured yet. Set SUPABASE_URL and keys, or use X-Dev-User-Id for scaffolding.',
        )

    # TODO: verify JWT against Supabase JWKS.
    raise HTTPException(
        status_code=501,
        detail='JWT verification scaffolding only. Configure Supabase + add JWKS verification next.',
    )


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
