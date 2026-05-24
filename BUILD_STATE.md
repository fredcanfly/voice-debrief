# Voice Debrief Build State (Single Source of Truth)

Last updated: 2026-05-24

## Working policy (always)
1. Build-first: ship the smallest runnable slice immediately.
2. Keep planning short (3–6 bullets max), then execute.
3. Every turn must change state (code/config/test/deploy validation).
4. Keep this file updated every iteration so context compaction never blocks progress.
5. End each update with one immediate next action.

## Roadmap source of truth
- `README.md` (feature/milestone status)
- `DEPLOYMENT.md` (beta deployment sequence)

## Current verified state
- Repo: `/home/trevis/voice-debrief`
- Backend is running and healthy on `:8787`.
- `GET /api/health` => ok
- `GET /api/beta/can-signup` => allowed=true
- Supabase connectivity is live and tables exist (`profiles`, `user_settings`, `debrief_sessions`, `debrief_turns`, `usage_monthly`).
- `.env` has Supabase keys and beta mode flags set.
- `SUPABASE_URL` is corrected to project root (not `/rest/v1/`).

## Important blocker discovered
- In multi-user mode, `/api/me/settings` fails if `X-Dev-User-Id` is not a UUID.
- Cause: DB schema uses `uuid` for `user_settings.user_id`; test header value `dev-check-1` is invalid for that type.
- Impact: local dev-header testing can look broken unless UUID-form IDs are used.

## Roadmap position (where we are)
### Done
- Local-first debrief loop (STT -> Hermes -> TTS)
- End debrief -> markdown save
- Hands-free flow + endpoint tuning telemetry
- Supabase-backed beta scaffolding and endpoints (`/api/me/settings`, `/api/beta/can-signup`)

### Not done yet (next roadmap items)
1. Full true continuous streaming/server-side VAD (websocket/chunk stream) in phone PWA.
2. Automatic Telegram delivery of final summary.
3. Production deploy path hardening (real domain/origin wiring at the right stage in your sequence).

## Work split
### Vicki can do now
1. Fix UUID handling for local dev-header path (auto-coerce or fallback) so `/api/me/settings` is robust.
2. Add/adjust tests for multi-user dev-header behavior.
3. Implement Telegram auto-delivery after final summary save.
4. Keep BUILD_STATE + mirrored Windows copy updated every iteration.

### Trevis needs to do
1. Supabase dashboard actions only if schema/policies need changes (already appears complete).
2. Later (not now): provide final deploy domain(s) when you decide to do URL setup stage.
3. Phone real-world acceptance test after each shipped slice.

## Next immediate action
- Implement the UUID-safe dev-header fix + tests, then re-run live `/api/me/settings` verification and report pass/fail.
