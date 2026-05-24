export function loadConfigFromEnv(env = process.env) {
  const discordToken = env.DISCORD_TOKEN?.trim();
  if (!discordToken) {
    throw new Error('DISCORD_TOKEN is required. Put your Discord bot token in discord-voice-bridge/.env.');
  }

  return {
    discordToken,
    bridgeBaseUrl: stripTrailingSlash(env.VOICE_BRIDGE_BASE_URL || 'http://127.0.0.1:8787'),
    commandPrefix: env.VICKI_COMMAND_PREFIX || '!vicki',
    silenceMs: parsePositiveInt(env.VICKI_SILENCE_MS, 750),
    maxUtteranceMs: parsePositiveInt(env.VICKI_MAX_UTTERANCE_MS, 15000),
    speakReplies: parseBool(env.VICKI_SPEAK_REPLIES, true),
  };
}

function stripTrailingSlash(value) {
  return String(value).replace(/\/+$/, '');
}

function parsePositiveInt(value, fallback) {
  if (value === undefined || value === null || value === '') return fallback;
  const parsed = Number.parseInt(String(value), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function parseBool(value, fallback) {
  if (value === undefined || value === null || value === '') return fallback;
  return !['0', 'false', 'no', 'off'].includes(String(value).trim().toLowerCase());
}
