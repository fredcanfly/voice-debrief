# Voice Debrief Beta Deployment (Railway + Cloudflare Pages + Supabase)

## Variables to edit first

Set these before first real deploy:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `PUBLIC_BASE_URL`
- `CORS_ALLOWED_ORIGINS`

Use `.env.example.beta` as the source template.

## Fast path build order

1. Copy `.env.example.beta` -> `.env` (local) and Railway env vars.
2. Deploy backend to Railway:
   - Start command: `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
3. Deploy frontend to Cloudflare Pages.
4. Set frontend env:
   - `VITE_API_BASE_URL`
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
5. Keep `BETA_SIGNUPS_OPEN=true` while invited users sign up.
6. After invited users are in, set `BETA_SIGNUPS_OPEN=false` and redeploy.

## Current scaffolding status

Implemented in backend:

- `GET /api/me/settings`
- `POST /api/me/settings`
- `GET /api/beta/can-signup`

Notes:

- These are scaffold endpoints with local JSON persistence under `data/`.
- JWT verification is intentionally scaffold-only until Supabase keys are real.
- Dev header fallback for local testing: `X-Dev-User-Id`.

## Next build slice

- Wire real Supabase JWT verification (JWKS)
- Replace local JSON profile/settings writes with Supabase tables
- Add frontend setup wizard route based on `/api/me/settings`
