import fs from 'node:fs';
import FormData from 'form-data';
import fetch from 'node-fetch';

export function makeSessionId(guildId, voiceChannelId) {
  return `discord-vc-${guildId}-${voiceChannelId}`;
}

export function buildBridgeAudioUrl(bridgeBaseUrl, audioUrl) {
  if (!audioUrl) return null;
  if (/^https?:\/\//i.test(audioUrl)) return audioUrl;
  return `${bridgeBaseUrl.replace(/\/+$/, '')}/${String(audioUrl).replace(/^\/+/, '')}`;
}

export async function startSession(config, sessionId) {
  const resp = await fetch(`${config.bridgeBaseUrl}/api/debrief/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  });
  await assertOk(resp, 'start debrief session');
  return resp.json();
}

export async function sendAudioTurn(config, sessionId, wavPath) {
  const form = new FormData();
  form.append('file', fs.createReadStream(wavPath), {
    filename: 'discord-turn.wav',
    contentType: 'audio/wav',
  });

  const url = new URL(`${config.bridgeBaseUrl}/api/debrief/audio`);
  url.searchParams.set('session_id', sessionId);
  url.searchParams.set('speak', config.speakReplies ? 'true' : 'false');

  const resp = await fetch(url, {
    method: 'POST',
    body: form,
    headers: form.getHeaders(),
  });
  await assertOk(resp, 'send audio turn');
  const data = await resp.json();
  return {
    ...data,
    playableAudioUrl: buildBridgeAudioUrl(config.bridgeBaseUrl, data.audio_url),
  };
}

async function assertOk(resp, action) {
  if (resp.ok) return;
  const text = await resp.text().catch(() => '');
  throw new Error(`Failed to ${action}: HTTP ${resp.status} ${resp.statusText} ${text}`);
}
