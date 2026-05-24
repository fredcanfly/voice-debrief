# Vicki Discord Voice Bridge

This is a live Discord voice-channel bridge for the existing `voice-debrief` FastAPI/Hermes bridge.

```text
Discord VC audio -> this Node bot -> /api/debrief/audio -> faster-whisper -> Hermes -> Edge TTS -> Discord VC
```

## What works in this prototype

- `!vicki join` joins the voice channel you are currently in.
- The bot listens for a speaker, stops recording after a short silence, and sends that utterance to the existing FastAPI bridge.
- The bridge transcribes with local `faster-whisper`, sends the text to Hermes, synthesizes an MP3 reply, and returns it.
- The Discord bot posts the transcript/reply in text and plays the MP3 into the voice channel.
- If someone starts talking while Vicki is playing audio, playback is stopped for basic barge-in behavior.

## Setup

### 1. Start the existing Hermes API server and voice-debrief bridge

From the parent `voice-debrief` directory, make sure Hermes API Server is enabled in `~/.hermes/.env`:

```bash
API_SERVER_ENABLED=true
API_SERVER_KEY=change-me-local-dev
API_SERVER_HOST=127.0.0.1
API_SERVER_PORT=8642
```

Restart Hermes gateway:

```bash
hermes gateway restart
```

Start the FastAPI bridge:

```bash
cd ~/voice-debrief
source .venv/bin/activate
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8787 --reload
```

Check it:

```bash
curl http://127.0.0.1:8787/api/health
```

### 2. Create a Discord bot

In the Discord Developer Portal:

1. Create an application + bot.
2. Copy the bot token.
3. Enable **Message Content Intent**.
4. Invite it to your server with permissions:
   - View Channels
   - Send Messages
   - Connect
   - Speak
   - Use Voice Activity

For a quick invite URL, use OAuth2 URL Generator with scopes `bot` and permissions for send/connect/speak.

### 3. Install and configure this bridge

```bash
cd ~/voice-debrief/discord-voice-bridge
npm install
cp .env.example .env
nano .env
```

Set:

```env
DISCORD_TOKEN=your-real-token
VOICE_BRIDGE_BASE_URL=http://127.0.0.1:8787
```

### 4. Run it

```bash
npm start
```

In Discord:

1. Join a voice channel.
2. In a text channel the bot can read, type:

```text
!vicki join
```

3. Speak, pause, and Vicki should answer out loud.
4. Disconnect with:

```text
!vicki leave
```

## Notes / limitations

- This is a first live-VC prototype, not a production Discord voice assistant.
- It uses Discord speaking events + silence timeout rather than neural VAD.
- Discord voice receive in Node depends on Opus native packages. If `npm install` fails, install build tools and try again.
- If the bot joins but does not hear users, verify it was invited with voice permissions and that `selfDeaf: false` is present in `src/index.js`.
- For fastest conversation, keep the existing Python bridge on GPU-backed faster-whisper, or switch that bridge to a cloud STT provider later.
