# Vicki Voice Debrief

Local-first prototype for Bob's hands-free meeting debrief flow.

## Architecture

```text
Phone PWA -> FastAPI bridge -> local faster-whisper STT -> Hermes API Server -> Edge TTS -> Phone/car speakers
```

This is intentionally separate from Hermes while the UX is still a prototype.

## Current MVP state

Implemented now:

- FastAPI bridge
- Hermes `/v1/responses` integration using named conversations
- Edge TTS replies
- Local `faster-whisper` transcription for uploaded audio files
- Simple PWA shell with text and audio-file test inputs
- Manual browser microphone recording: tap **Record**, speak, tap **Stop Recording**, then Vicki transcribes/replies/speaks
- End Debrief flow: generates structured final notes, saves markdown under `/mnt/c/Users/Trevis/Documents/Phone/debriefs/`, and shows an open/copy summary UI
- Smart final-note titles: Vicki now emits a specific `Title:` line, and saved markdown filenames use that title, for example `2026-05-22-1530-product-roadmap-update.md`
- Car-mode UI: large Start/Record/End controls, sticky status, advanced testing controls collapsed away, and optional screen wake lock
- Browser-side silence auto-stop: when enabled, tap **Record**, speak, then Vicki automatically stops and sends the turn after a short pause
- Hands-free continue: after Vicki finishes speaking, the browser automatically opens the mic again for the next turn
- Continuous mic session (phase 2): one long-running browser recorder now pauses/flushes turns with chunk boundaries (`requestData` + `pause`) and resumes for the next turn
- Server-side endpointing guard (phase 3): local STT metadata (`speech_seconds` + text length) now filters short/noisy turn flushes before they hit Hermes, then reopens listening
- Endpoint telemetry (phase 4): backend tracks accepted vs filtered turns and exposes `GET /api/debug/endpoint-stats`; Advanced testing controls now show live endpoint stats + active thresholds
- Runtime tuning + persistence (phase 4B): Advanced testing controls can update endpoint thresholds live, and the bridge saves them to `data/endpoint_tuning.json` so settings survive restart
- Spoken wrap-up commands: full-utterance commands like **stop**, **stop debrief**, **end debrief**, **wrap it up**, **save this**, and **finish** trigger the final summary/save flow
- Barge-in interrupt: while Vicki is speaking, tap **Record** to immediately cut playback and start recording your next turn

Not implemented yet in the phone PWA:

- Full server-side VAD from truly continuous audio streaming (websocket/chunk feed)
- Automatic Telegram delivery of final summary

Discord voice-channel prototype moved out of this project:

- Use `~/vicki-discord-voice/` for conversational Discord voice chat. It runs on a separate port and has separate prompts/data so this debrief app can run at the same time.

## Hermes API Server setup

Edit `~/.hermes/.env` and add:

```bash
API_SERVER_ENABLED=true
API_SERVER_KEY=change-me-local-dev
API_SERVER_HOST=127.0.0.1
API_SERVER_PORT=8642
```

Restart the Hermes gateway:

```bash
hermes gateway restart
# or foreground:
hermes gateway run
```

Check:

```bash
curl -H "Authorization: Bearer change-me-local-dev" http://127.0.0.1:8642/v1/health
```

## Bridge setup

```bash
cd ~/voice-debrief
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
cp .env.example .env
```

Final markdown debriefs are saved to the Windows Documents folder by default:

```text
/mnt/c/Users/Trevis/Documents/Phone/debriefs
```

Override with `DEBRIEF_OUTPUT_DIR` in `.env` if needed.

Your WSL environment can see the RTX 3080 through `/usr/lib/wsl/lib/nvidia-smi`. If CUDA packages are unhappy, first verify:

```bash
/usr/lib/wsl/lib/nvidia-smi
```

Run the bridge:

```bash
source .venv/bin/activate
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8787 --reload
```

Open on the bridge machine:

```text
http://localhost:8787
```

## Local STT benchmark

Use any voice memo/audio file:

```bash
source .venv/bin/activate
python -m backend.benchmark_stt /path/to/voice-memo.m4a
```

Default config:

```env
WHISPER_MODEL=small
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
WHISPER_VAD_MIN_SILENCE_MS=700
ENDPOINT_MIN_SPEECH_SECONDS=0.55
ENDPOINT_MIN_TEXT_CHARS=8
```

For RTX 3080, try these in order:

1. `small` + `cuda` + `float16` — likely fast enough and good quality.
2. `medium` + `cuda` + `float16` — better quality if latency is acceptable.
3. `base` + `cuda` + `float16` — faster fallback.
4. `small` + `cpu` + `int8` — fallback if CUDA setup breaks.

## Phone access

### Tailscale

Tailscale's Personal plan is currently suitable for this use case: 1 user and up to 100 devices. Verify current limits before relying on it long-term.

Use Tailscale when you want private phone-to-home access without exposing the bridge publicly.

Caveat: browser microphone access from a phone generally requires HTTPS for non-localhost origins. Tailscale gives private routing, but you may still need HTTPS certs for the PWA.

### Cloudflare Tunnel

Cloudflare Tunnel is probably easier for HTTPS/PWA microphone permissions. If exposing the bridge publicly, add access control before real use.

Recommended for first driving test if you already know Cloudflare Tunnel:

```bash
cloudflared tunnel --url http://localhost:8787
```

Use the generated `https://...trycloudflare.com` URL from your phone.

## Test flow

1. Start Hermes API Server.
2. Start this bridge.
3. Open the PWA.
4. Tap **Start Debrief**.
5. Send a typed test message.
6. Confirm Vicki replies with text and audio.
7. Leave **Silence Auto-Stop** and **Hands-Free Continue** on, tap **Record**, speak one thought, then pause; Vicki should stop recording, send the turn, reply, then reopen the mic automatically.
8. Keep talking in turns by waiting for **Listening again. Start talking.** after each Vicki reply.
9. Say **stop** as a standalone turn to verify Vicki hears the voice command, stops the hands-free loop, generates final notes, and saves the markdown.
10. Other supported wrap-up commands are **stop debrief**, **end debrief**, **wrap it up**, **save this**, and **finish**.
11. Toggle **Hands-Free Continue** off if you want one-turn-at-a-time mode.
12. Toggle **Silence Auto-Stop** off if you want manual mode, then tap **Record** and **Stop Recording** yourself.
13. Confirm local transcription + Hermes reply + spoken response.
14. Optionally upload a voice memo/audio file with **Audio file test**.
15. Tap **End Debrief** if you did not use a voice command.
16. Confirm final notes appear in the **Final notes** card.
17. Use **Open saved markdown** or **Copy summary** as needed.
18. Check `/mnt/c/Users/Trevis/Documents/Phone/debriefs/` for the saved final markdown and `data/transcripts/` for the raw turn transcript. The final markdown filename should include the date/time and Vicki's inferred title, such as `2026-05-22-1530-product-roadmap-update.md`.

## Mic recording notes

The PWA uses the browser `MediaRecorder` API. On desktop `localhost`, microphone access should work over plain HTTP. On a phone, mic access normally requires an HTTPS origin, so use Cloudflare Tunnel or another HTTPS route for mobile testing.

Current behavior uses utterance-level browser recording:

```text
Record once -> speak -> pause -> recorder flushes turn (`requestData` + pause) -> upload utterance blob -> faster-whisper -> Hermes -> Edge TTS -> recorder resumes for next turn
```

You can turn **Hands-Free Continue** off if you want the mic to stay closed after Vicki replies. You can turn **Silence Auto-Stop** off to return to manual `Record -> tap again to send current turn` mode.

Spoken wrap-up commands are matched as full normalized utterances, not loose keywords. Saying **stop** by itself ends and saves the debrief; saying “we need to stop doing that” is treated as a normal debrief turn.

The next milestone is continuous streaming/server-side VAD if the browser-only auto-stop does not feel smooth enough during driving tests.
