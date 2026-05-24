import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { pipeline } from 'node:stream/promises';

import {
  AudioPlayerStatus,
  EndBehaviorType,
  VoiceConnectionStatus,
  createAudioPlayer,
  createAudioResource,
  entersState,
  getVoiceConnection,
  joinVoiceChannel,
} from '@discordjs/voice';
import { Client, GatewayIntentBits, Partials } from 'discord.js';
import dotenv from 'dotenv';
import prism from 'prism-media';

import { sendAudioTurn, startSession, makeSessionId } from './bridgeClient.js';
import { loadConfigFromEnv } from './config.js';
import { createWavBuffer } from './wav.js';

dotenv.config();

const config = loadConfigFromEnv();
const playersByGuild = new Map();
const activeRecordings = new Set();

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.GuildVoiceStates,
    GatewayIntentBits.MessageContent,
  ],
  partials: [Partials.Channel],
});

client.once('ready', () => {
  console.log(`Vicki Discord voice bridge logged in as ${client.user.tag}`);
  console.log(`Command prefix: ${config.commandPrefix}`);
  console.log(`Voice bridge API: ${config.bridgeBaseUrl}`);
});

client.on('messageCreate', async (message) => {
  if (message.author.bot || !message.guild) return;
  if (!message.content.startsWith(config.commandPrefix)) return;

  const args = message.content.slice(config.commandPrefix.length).trim().split(/\s+/).filter(Boolean);
  const command = (args.shift() || 'help').toLowerCase();

  try {
    if (command === 'join') {
      await joinAuthorVoice(message);
    } else if (command === 'leave') {
      const connection = getVoiceConnection(message.guild.id);
      if (connection) connection.destroy();
      playersByGuild.delete(message.guild.id);
      await message.reply('Left voice chat.');
    } else if (command === 'help') {
      await message.reply(
        `Commands: \`${config.commandPrefix} join\` to join your current VC, `
        + `\`${config.commandPrefix} leave\` to disconnect.`,
      );
    }
  } catch (error) {
    console.error(error);
    await message.reply(`Voice bridge error: ${error.message}`);
  }
});

async function joinAuthorVoice(message) {
  const voiceChannel = message.member?.voice?.channel;
  if (!voiceChannel) {
    await message.reply('Join a voice channel first, then run the join command again.');
    return;
  }

  const connection = joinVoiceChannel({
    channelId: voiceChannel.id,
    guildId: message.guild.id,
    adapterCreator: message.guild.voiceAdapterCreator,
    selfDeaf: false,
    selfMute: false,
  });

  const player = createAudioPlayer();
  connection.subscribe(player);
  playersByGuild.set(message.guild.id, player);

  await entersState(connection, VoiceConnectionStatus.Ready, 30_000);

  const sessionId = makeSessionId(message.guild.id, voiceChannel.id);
  await startSession(config, sessionId);
  attachReceiver(connection, message, sessionId);

  await message.reply(`Joined **${voiceChannel.name}**. Say something, pause, and I’ll answer out loud.`);
}

function attachReceiver(connection, message, sessionId) {
  const keyPrefix = `${connection.joinConfig.guildId}:`;
  connection.receiver.speaking.on('start', (userId) => {
    const key = `${keyPrefix}${userId}`;
    if (activeRecordings.has(key)) return;
    activeRecordings.add(key);

    handleUtterance(connection, message, sessionId, userId, key).catch(async (error) => {
      console.error(error);
      await message.channel.send(`Voice processing error: ${error.message}`);
    }).finally(() => {
      activeRecordings.delete(key);
    });
  });
}

async function handleUtterance(connection, message, sessionId, userId, activeKey) {
  const player = playersByGuild.get(connection.joinConfig.guildId);
  if (player?.state.status === AudioPlayerStatus.Playing) {
    // Barge-in: stop Vicki if a human starts speaking.
    player.stop(true);
  }

  const opusStream = connection.receiver.subscribe(userId, {
    end: {
      behavior: EndBehaviorType.AfterSilence,
      duration: config.silenceMs,
    },
  });

  const decoder = new prism.opus.Decoder({ rate: 48000, channels: 1, frameSize: 960 });
  const chunks = [];
  decoder.on('data', (chunk) => chunks.push(chunk));

  const timeout = setTimeout(() => opusStream.destroy(), config.maxUtteranceMs);
  try {
    await pipeline(opusStream, decoder);
  } finally {
    clearTimeout(timeout);
  }

  if (!activeRecordings.has(activeKey) || chunks.length === 0) return;

  const pcm = Buffer.concat(chunks);
  // Ignore tiny noises/clicks. 48kHz * 2 bytes = 96 KB/sec.
  if (pcm.length < 24_000) return;

  const wav = createWavBuffer(pcm, { sampleRate: 48000, channels: 1, bitDepth: 16 });
  const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), 'vicki-discord-'));
  const wavPath = path.join(tmpDir, `${Date.now()}-${userId}.wav`);
  await fs.writeFile(wavPath, wav);

  try {
    await message.channel.sendTyping();
    const reply = await sendAudioTurn(config, sessionId, wavPath);
    if (reply.transcript_text) {
      await message.channel.send(`**${await displayName(message, userId)}:** ${reply.transcript_text}\n**Vicki:** ${reply.reply_text}`);
    }
    if (reply.playableAudioUrl) {
      await playReply(connection, reply.playableAudioUrl);
    }
  } finally {
    await fs.rm(tmpDir, { recursive: true, force: true });
  }
}

async function displayName(message, userId) {
  const member = await message.guild.members.fetch(userId).catch(() => null);
  return member?.displayName || `User ${userId}`;
}

async function playReply(connection, audioUrl) {
  const player = playersByGuild.get(connection.joinConfig.guildId) || createAudioPlayer();
  playersByGuild.set(connection.joinConfig.guildId, player);
  connection.subscribe(player);
  const resource = createAudioResource(audioUrl);
  player.play(resource);
}

client.login(config.discordToken);
