import test from 'node:test';
import assert from 'node:assert/strict';

import { loadConfigFromEnv } from '../src/config.js';
import { buildBridgeAudioUrl, makeSessionId } from '../src/bridgeClient.js';
import { createWavBuffer } from '../src/wav.js';

test('loadConfigFromEnv parses required and optional values', () => {
  const config = loadConfigFromEnv({
    DISCORD_TOKEN: 'token-123',
    VOICE_BRIDGE_BASE_URL: 'http://localhost:8787/',
    VICKI_COMMAND_PREFIX: '!v',
    VICKI_SILENCE_MS: '900',
    VICKI_MAX_UTTERANCE_MS: '12000',
    VICKI_SPEAK_REPLIES: 'false',
  });

  assert.equal(config.discordToken, 'token-123');
  assert.equal(config.bridgeBaseUrl, 'http://localhost:8787');
  assert.equal(config.commandPrefix, '!v');
  assert.equal(config.silenceMs, 900);
  assert.equal(config.maxUtteranceMs, 12000);
  assert.equal(config.speakReplies, false);
});

test('loadConfigFromEnv throws a helpful error without DISCORD_TOKEN', () => {
  assert.throws(
    () => loadConfigFromEnv({}),
    /DISCORD_TOKEN is required/,
  );
});

test('makeSessionId is stable for guild and voice channel', () => {
  assert.equal(makeSessionId('guild-a', 'voice-b'), 'discord-vc-guild-a-voice-b');
});

test('buildBridgeAudioUrl joins the public base URL and bridge audio path', () => {
  assert.equal(
    buildBridgeAudioUrl('https://example.ngrok-free.app/', '/audio/reply.mp3'),
    'https://example.ngrok-free.app/audio/reply.mp3',
  );
});

test('createWavBuffer wraps 48 kHz mono signed 16-bit PCM with a valid WAV header', () => {
  const pcm = Buffer.from([1, 0, 255, 255]); // two int16 samples
  const wav = createWavBuffer(pcm, { sampleRate: 48000, channels: 1, bitDepth: 16 });

  assert.equal(wav.subarray(0, 4).toString('ascii'), 'RIFF');
  assert.equal(wav.subarray(8, 12).toString('ascii'), 'WAVE');
  assert.equal(wav.subarray(12, 16).toString('ascii'), 'fmt ');
  assert.equal(wav.readUInt16LE(22), 1); // channels
  assert.equal(wav.readUInt32LE(24), 48000); // sample rate
  assert.equal(wav.subarray(36, 40).toString('ascii'), 'data');
  assert.equal(wav.readUInt32LE(40), pcm.length);
  assert.deepEqual(wav.subarray(44), pcm);
});
