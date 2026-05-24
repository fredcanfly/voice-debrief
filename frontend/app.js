let sessionId = null;
let mediaRecorder = null;
let recordStartedAt = 0;
let recordTimerId = null;
let wakeLockSentinel = null;
let autoStopEnabled = true;
let autoContinueEnabled = true;
let audioContext = null;
let analyserNode = null;
let silenceMonitorId = null;
let currentPlaybackAudio = null;
let micStream = null;
let silenceStartedAt = null;
let recordingGraceEndsAt = 0;
let heardSpeech = false;
let turnFlushInFlight = false;
let flushPromiseResolve = null;

const AUTO_STOP_SILENCE_MS = 1300;
const AUTO_STOP_GRACE_MS = 900;
const AUTO_STOP_SPEECH_RMS = 0.035;
const VOICE_END_COMMANDS = new Set([
  'stop',
  'stop debrief',
  'end debrief',
  'wrap it up',
  'save this',
  'finish',
]);

const statusEl = document.getElementById('status');
const logEl = document.getElementById('log');
const startBtn = document.getElementById('start');
const endBtn = document.getElementById('end');
const sendBtn = document.getElementById('send');
const sendAudioBtn = document.getElementById('sendAudio');
const recordBtn = document.getElementById('record');
const recordTimerEl = document.getElementById('recordTimer');
const messageEl = document.getElementById('message');
const audioFileEl = document.getElementById('audioFile');
const summaryTextEl = document.getElementById('summaryText');
const summaryActionsEl = document.getElementById('summaryActions');
const summaryLinkEl = document.getElementById('summaryLink');
const copySummaryBtn = document.getElementById('copySummary');
const wakeLockBtn = document.getElementById('wakeLock');
const autoStopBtn = document.getElementById('autoStop');
const autoStopStateEl = document.getElementById('autoStopState');
const autoContinueBtn = document.getElementById('autoContinue');
const autoContinueStateEl = document.getElementById('autoContinueState');
const endpointStatsEl = document.getElementById('endpointStats');
const endpointThresholdsEl = document.getElementById('endpointThresholds');
const endpointMinSpeechEl = document.getElementById('endpointMinSpeech');
const endpointMinCharsEl = document.getElementById('endpointMinChars');
const endpointVadSilenceEl = document.getElementById('endpointVadSilence');
const applyEndpointTuningBtn = document.getElementById('applyEndpointTuning');
const applyDrivingPresetBtn = document.getElementById('applyDrivingPreset');
const applyOfficePresetBtn = document.getElementById('applyOfficePreset');
const resetEndpointTuningBtn = document.getElementById('resetEndpointTuning');

function setStatus(text) { statusEl.textContent = text; }
function addLog(speaker, text) {
  const div = document.createElement('div');
  div.className = 'entry';
  div.innerHTML = `<div class="speaker"></div><div></div>`;
  div.children[0].textContent = speaker;
  div.children[1].textContent = text;
  logEl.prepend(div);
}
function stopPlayback(reason = 'Playback stopped.') {
  if (!currentPlaybackAudio) return false;
  const audio = currentPlaybackAudio;
  currentPlaybackAudio = null;
  audio.pause();
  audio.currentTime = 0;
  setStatus(reason);
  return true;
}
async function playAudio(url) {
  if (!url) return;
  stopPlayback();
  const audio = new Audio(url);
  currentPlaybackAudio = audio;
  await new Promise(resolve => {
    const cleanup = () => {
      if (currentPlaybackAudio === audio) currentPlaybackAudio = null;
      audio.onended = null;
      audio.onerror = null;
      resolve();
    };
    audio.onended = cleanup;
    audio.onerror = cleanup;
    audio.play().catch(cleanup);
  });
}
async function postJson(url, body) {
  const res = await fetch(url, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
async function refreshEndpointStats() {
  if (!endpointStatsEl || !endpointThresholdsEl) return;
  try {
    const res = await fetch('/api/debug/endpoint-stats');
    if (!res.ok) throw new Error('stats unavailable');
    const data = await res.json();
    const accepted = Number(data.accepted_turns || 0);
    const filtered = Number(data.filtered_turns || 0);
    const rate = Math.round(Number(data.filtered_rate || 0) * 100);
    endpointStatsEl.textContent = `accepted: ${accepted} · filtered: ${filtered} · rate: ${rate}%`;

    const thresholds = data.thresholds || {};
    const minSpeech = thresholds.endpoint_min_speech_seconds ?? '?';
    const minChars = thresholds.endpoint_min_text_chars ?? '?';
    const vadSilence = thresholds.whisper_vad_min_silence_ms ?? '?';
    endpointThresholdsEl.textContent = `speech≥${minSpeech}s · chars≥${minChars} · VAD silence ${vadSilence}ms`;

    if (endpointMinSpeechEl && Number.isFinite(Number(minSpeech))) endpointMinSpeechEl.value = String(minSpeech);
    if (endpointMinCharsEl && Number.isFinite(Number(minChars))) endpointMinCharsEl.value = String(minChars);
    if (endpointVadSilenceEl && Number.isFinite(Number(vadSilence))) endpointVadSilenceEl.value = String(vadSilence);
  } catch (_) {
    endpointStatsEl.textContent = 'accepted: ? · filtered: ? · rate: ?';
  }
}
async function applyEndpointTuning() {
  if (!applyEndpointTuningBtn) return;
  const endpoint_min_speech_seconds = Number(endpointMinSpeechEl?.value || 0);
  const endpoint_min_text_chars = Number(endpointMinCharsEl?.value || 0);
  const whisper_vad_min_silence_ms = Number(endpointVadSilenceEl?.value || 0);

  if (!Number.isFinite(endpoint_min_speech_seconds) || endpoint_min_speech_seconds < 0 || endpoint_min_speech_seconds > 5) {
    setStatus('Endpoint tuning error: min speech seconds must be between 0 and 5.');
    return;
  }
  if (!Number.isFinite(endpoint_min_text_chars) || endpoint_min_text_chars < 0 || endpoint_min_text_chars > 120) {
    setStatus('Endpoint tuning error: min text chars must be between 0 and 120.');
    return;
  }
  if (!Number.isFinite(whisper_vad_min_silence_ms) || whisper_vad_min_silence_ms < 0 || whisper_vad_min_silence_ms > 5000) {
    setStatus('Endpoint tuning error: VAD silence ms must be between 0 and 5000.');
    return;
  }

  applyEndpointTuningBtn.disabled = true;
  try {
    const res = await fetch('/api/debug/endpoint-thresholds', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        endpoint_min_speech_seconds,
        endpoint_min_text_chars,
        whisper_vad_min_silence_ms,
      }),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    const rate = Math.round(Number(data.filtered_rate || 0) * 100);
    setStatus(`Endpoint tuning applied. Filter rate: ${rate}%.`);
    await refreshEndpointStats();
  } catch (error) {
    setStatus(`Endpoint tuning error: ${error.message}`);
  } finally {
    applyEndpointTuningBtn.disabled = false;
  }
}

async function applyEndpointPreset(presetName) {
  const res = await fetch('/api/debug/endpoint-thresholds', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ preset: presetName }),
  });
  if (!res.ok) throw new Error(await res.text());
  await refreshEndpointStats();
}

async function resetEndpointTuning() {
  const res = await fetch('/api/debug/endpoint-thresholds', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ reset_to_defaults: true }),
  });
  if (!res.ok) throw new Error(await res.text());
  await refreshEndpointStats();
}

async function applyDrivingPreset() {
  await applyEndpointPreset('driving');
}

async function applyOfficePreset() {
  await applyEndpointPreset('office');
}
function setDebriefControls(active) {
  startBtn.disabled = active;
  endBtn.disabled = !active;
  sendBtn.disabled = !active;
  sendAudioBtn.disabled = !active;
  recordBtn.disabled = !active || !navigator.mediaDevices || !window.MediaRecorder;
}
function setBusy(isBusy) {
  if (!sessionId) return;
  sendBtn.disabled = isBusy;
  sendAudioBtn.disabled = isBusy;
  recordBtn.disabled = isBusy;
  endBtn.disabled = isBusy;
}
function formatElapsed(ms) {
  const total = Math.floor(ms / 1000);
  const minutes = String(Math.floor(total / 60)).padStart(2, '0');
  const seconds = String(total % 60).padStart(2, '0');
  return `${minutes}:${seconds}`;
}
function startTimer() {
  recordStartedAt = Date.now();
  recordTimerEl.textContent = '00:00';
  recordTimerId = window.setInterval(() => {
    recordTimerEl.textContent = formatElapsed(Date.now() - recordStartedAt);
  }, 250);
}
function stopTimer() {
  if (recordTimerId) window.clearInterval(recordTimerId);
  recordTimerId = null;
}
function updateAutoStopButton() {
  if (!autoStopBtn) return;
  autoStopBtn.textContent = autoStopEnabled ? 'Silence Auto-Stop On' : 'Silence Auto-Stop Off';
  autoStopBtn.classList.toggle('active', autoStopEnabled);
  if (autoStopStateEl) {
    autoStopStateEl.textContent = autoStopEnabled
      ? 'After you talk, Vicki will stop recording when you pause.'
      : 'Manual mode. Tap Stop Recording when done.';
  }
}
function updateAutoContinueButton() {
  if (!autoContinueBtn) return;
  autoContinueBtn.textContent = autoContinueEnabled ? 'Hands-Free Continue On' : 'Hands-Free Continue Off';
  autoContinueBtn.classList.toggle('active', autoContinueEnabled);
  if (autoContinueStateEl) {
    autoContinueStateEl.textContent = autoContinueEnabled
      ? 'After Vicki replies, the mic opens again for your next turn.'
      : 'One turn at a time. Tap Record for each turn.';
  }
}
function shouldAutoContinue() {
  return Boolean(sessionId && autoStopEnabled && autoContinueEnabled && navigator.mediaDevices && window.MediaRecorder);
}
function normalizeVoiceCommand(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/[.,!?;:]+$/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}
function isEndDebriefVoiceCommand(text) {
  return VOICE_END_COMMANDS.has(normalizeVoiceCommand(text));
}
function createAnalyser(stream) {
  if (!window.AudioContext && !window.webkitAudioContext) return null;
  audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const source = audioContext.createMediaStreamSource(stream);
  analyserNode = audioContext.createAnalyser();
  analyserNode.fftSize = 2048;
  source.connect(analyserNode);
  return analyserNode;
}
function stopSilenceMonitor() {
  if (silenceMonitorId) window.cancelAnimationFrame(silenceMonitorId);
  silenceMonitorId = null;
  silenceStartedAt = null;
  analyserNode = null;
  if (audioContext) {
    audioContext.close().catch(() => {});
    audioContext = null;
  }
}
async function getMicStream() {
  if (micStream && micStream.getTracks().some(track => track.readyState === 'live')) return micStream;
  micStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      channelCount: 1,
    },
    video: false,
  });
  return micStream;
}
function releaseMicStream() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
  mediaRecorder = null;
  if (!micStream) return;
  micStream.getTracks().forEach(track => track.stop());
  micStream = null;
}
function handleRecorderIdleUI() {
  stopTimer();
  stopSilenceMonitor();
  recordBtn.classList.remove('recording');
  recordBtn.textContent = 'Record';
}
async function processRecordedTurnBlob(blob, type) {
  if (blob.size < 1024) {
    setStatus('Recording was too short. Try again.');
    return;
  }
  await sendAudioBlob(blob, `recording.${extensionForMime(type)}`);
}
async function flushCurrentTurn(statusText = 'Sending turn...') {
  if (!mediaRecorder || mediaRecorder.state !== 'recording' || turnFlushInFlight) return false;
  turnFlushInFlight = true;
  setStatus(statusText);
  mediaRecorder.requestData();
  mediaRecorder.pause();
  handleRecorderIdleUI();
  return new Promise(resolve => {
    flushPromiseResolve = resolve;
  });
}
function ensureRecorderHandlers(mimeType) {
  mediaRecorder.ondataavailable = async event => {
    const resolveFlush = flushPromiseResolve;
    flushPromiseResolve = null;
    try {
      if (!event.data || event.data.size === 0) {
        turnFlushInFlight = false;
        if (resolveFlush) resolveFlush(false);
        return;
      }
      const type = mediaRecorder.mimeType || mimeType || 'audio/webm';
      await processRecordedTurnBlob(event.data, type);
      turnFlushInFlight = false;
      if (resolveFlush) resolveFlush(true);
    } catch (_) {
      turnFlushInFlight = false;
      if (resolveFlush) resolveFlush(false);
    }
  };
  mediaRecorder.onstop = () => {
    handleRecorderIdleUI();
    if (flushPromiseResolve) {
      flushPromiseResolve(false);
      flushPromiseResolve = null;
    }
    turnFlushInFlight = false;
    mediaRecorder = null;
  };
}
function monitorSilence() {
  if (!autoStopEnabled || !analyserNode || !mediaRecorder || mediaRecorder.state !== 'recording') return;
  const samples = new Uint8Array(analyserNode.fftSize);
  analyserNode.getByteTimeDomainData(samples);
  let sumSquares = 0;
  for (const sample of samples) {
    const value = (sample - 128) / 128;
    sumSquares += value * value;
  }
  const rms = Math.sqrt(sumSquares / samples.length);
  const now = Date.now();
  if (now < recordingGraceEndsAt) {
    silenceMonitorId = requestAnimationFrame(monitorSilence);
    return;
  }
  if (rms >= AUTO_STOP_SPEECH_RMS) {
    heardSpeech = true;
    silenceStartedAt = null;
  } else if (heardSpeech) {
    if (!silenceStartedAt) silenceStartedAt = now;
    if (now - silenceStartedAt >= AUTO_STOP_SILENCE_MS) {
      flushCurrentTurn('Silence detected. Sending turn...');
      return;
    }
  }
  silenceMonitorId = requestAnimationFrame(monitorSilence);
}
function preferredMimeType() {
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg;codecs=opus',
  ];
  return candidates.find(type => MediaRecorder.isTypeSupported(type)) || '';
}
function extensionForMime(mimeType) {
  if (mimeType.includes('mp4')) return 'm4a';
  if (mimeType.includes('ogg')) return 'ogg';
  return 'webm';
}
function updateWakeLockButton() {
  if (!wakeLockBtn) return;
  if (!('wakeLock' in navigator)) {
    wakeLockBtn.textContent = 'Screen Wake Unavailable';
    wakeLockBtn.disabled = true;
    return;
  }
  wakeLockBtn.textContent = wakeLockSentinel ? 'Screen Awake On' : 'Keep Screen Awake';
  wakeLockBtn.classList.toggle('active', Boolean(wakeLockSentinel));
}
async function requestWakeLock() {
  if (!('wakeLock' in navigator)) {
    setStatus('Screen wake lock is not supported here.');
    updateWakeLockButton();
    return;
  }
  wakeLockSentinel = await navigator.wakeLock.request('screen');
  wakeLockSentinel.addEventListener('release', () => {
    wakeLockSentinel = null;
    updateWakeLockButton();
  });
  updateWakeLockButton();
  setStatus('Ready. Screen will stay awake.');
}
async function releaseWakeLock() {
  if (!wakeLockSentinel) return;
  const lock = wakeLockSentinel;
  wakeLockSentinel = null;
  await lock.release();
  updateWakeLockButton();
  setStatus('Ready. Screen wake lock off.');
}

startBtn.onclick = async () => {
  setStatus('Starting...');
  const data = await postJson('/api/debrief/start', {});
  sessionId = data.session_id;
  await refreshEndpointStats();
  summaryTextEl.textContent = '';
  summaryActionsEl.classList.add('hidden');
  summaryLinkEl.removeAttribute('href');
  setDebriefControls(true);
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    setStatus('Debrief active. Browser does not support mic recording here.');
  } else {
    setStatus('Ready. Tap Record when you want to talk.');
    updateAutoStopButton();
    updateAutoContinueButton();
  }
};

sendBtn.onclick = async () => {
  const text = messageEl.value.trim();
  if (!text || !sessionId) return;
  messageEl.value = '';
  addLog('Bob', text);
  setBusy(true);
  setStatus('Vicki is thinking...');
  try {
    const data = await postJson('/api/debrief/message', { session_id: sessionId, text, speak: true });
    addLog('Vicki', data.reply_text);
    setBusy(false);
    setStatus('Vicki speaking. Tap Record to interrupt.');
    await playAudio(data.audio_url);
    if (shouldAutoContinue()) await startRecordingTurn();
  } catch (error) {
    setStatus(`Error: ${error.message}`);
  } finally {
    setBusy(false);
  }
};

sendAudioBtn.onclick = async () => {
  const file = audioFileEl.files[0];
  if (!file || !sessionId) return;
  await sendAudioBlob(file, file.name || 'upload.webm');
};

recordBtn.onclick = async () => {
  if (!sessionId) return;
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    await flushCurrentTurn('Sending turn...');
    return;
  }
  await startRecordingTurn();
};

async function startRecordingTurn() {
  if (!sessionId) return;
  if (turnFlushInFlight) return;
  stopPlayback('Interrupted Vicki. Listening now...');
  try {
    const stream = await getMicStream();
    const mimeType = preferredMimeType();
    if (!mediaRecorder) {
      mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      ensureRecorderHandlers(mimeType);
      mediaRecorder.start();
      await new Promise(resolve => {
        mediaRecorder.onstart = () => resolve();
        setTimeout(resolve, 80);
      });
    } else if (mediaRecorder.state === 'paused') {
      mediaRecorder.resume();
    } else if (mediaRecorder.state === 'inactive') {
      mediaRecorder.start();
    } else if (mediaRecorder.state === 'recording') {
      return;
    }
    heardSpeech = false;
    silenceStartedAt = null;
    recordingGraceEndsAt = Date.now() + AUTO_STOP_GRACE_MS;
    createAnalyser(stream);
    if (analyserNode) silenceMonitorId = requestAnimationFrame(monitorSilence);
    recordBtn.classList.add('recording');
    recordBtn.textContent = autoStopEnabled ? 'Listening…' : 'Pause + Send Turn';
    startTimer();
    setStatus(autoStopEnabled ? 'Listening again. Start talking.' : 'Recording. Tap Stop when done.');
  } catch (error) {
    setStatus(`Mic error: ${error.message}`);
  }
}

async function sendAudioBlob(blob, filename) {
  if (!sessionId) return;
  const form = new FormData();
  form.append('file', blob, filename);
  setBusy(true);
  setStatus('Transcribing audio locally...');
  try {
    const res = await fetch(`/api/debrief/audio?session_id=${encodeURIComponent(sessionId)}&speak=true`, { method: 'POST', body: form });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    if (data.no_turn) {
      await refreshEndpointStats();
      setStatus('Heard a short/noisy turn. Keep going.');
      if (shouldAutoContinue()) await startRecordingTurn();
      return;
    }
    if (data.transcript_text) addLog('Bob', data.transcript_text);
    if (data.transcript_text && isEndDebriefVoiceCommand(data.transcript_text)) {
      await refreshEndpointStats();
      setStatus('Voice command heard. Saving final notes...');
      await finishDebrief();
      return;
    }
    await refreshEndpointStats();
    addLog('Vicki', data.reply_text);
    setBusy(false);
    setStatus('Vicki speaking. Tap Record to interrupt.');
    await playAudio(data.audio_url);
    if (shouldAutoContinue()) await startRecordingTurn();
  } catch (error) {
    setStatus(`Error: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

endBtn.onclick = async () => {
  await finishDebrief();
};

async function finishDebrief() {
  if (!sessionId) return;
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
  stopPlayback('Ending debrief...');
  setBusy(true);
  setStatus('Saving final notes...');
  try {
    const data = await postJson('/api/debrief/end', { session_id: sessionId, text: 'end debrief', speak: true });
    addLog('Final summary', data.reply_text);
    summaryTextEl.textContent = data.reply_text;
    if (data.final_title) setStatus(`Debrief saved: ${data.final_title}`);
    if (data.final_markdown_url) {
      summaryLinkEl.href = data.final_markdown_url;
      summaryActionsEl.classList.remove('hidden');
    }
    await playAudio(data.audio_url);
    if (!data.final_title) setStatus('Debrief saved.');
    sessionId = null;
    releaseMicStream();
    setDebriefControls(false);
  } catch (error) {
    setStatus(`Error: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

copySummaryBtn.onclick = async () => {
  const text = summaryTextEl.textContent.trim();
  if (!text) return;
  await navigator.clipboard.writeText(text);
  setStatus('Summary copied.');
};

autoStopBtn.onclick = () => {
  autoStopEnabled = !autoStopEnabled;
  updateAutoStopButton();
  setStatus(autoStopEnabled ? 'Silence auto-stop on.' : 'Manual recording mode.');
};

autoContinueBtn.onclick = () => {
  autoContinueEnabled = !autoContinueEnabled;
  updateAutoContinueButton();
  setStatus(autoContinueEnabled ? 'Auto-continue on. I’ll reopen the mic after Vicki replies.' : 'Auto-continue off.');
};

wakeLockBtn.onclick = async () => {
  try {
    if (wakeLockSentinel) {
      await releaseWakeLock();
    } else {
      await requestWakeLock();
    }
  } catch (error) {
    setStatus(`Screen wake error: ${error.message}`);
  }
};

if (applyEndpointTuningBtn) {
  applyEndpointTuningBtn.onclick = applyEndpointTuning;
}
if (applyDrivingPresetBtn) {
  applyDrivingPresetBtn.onclick = async () => {
    try {
      await applyDrivingPreset();
      setStatus('Driving preset applied.');
    } catch (error) {
      setStatus(`Endpoint tuning error: ${error.message}`);
    }
  };
}
if (applyOfficePresetBtn) {
  applyOfficePresetBtn.onclick = async () => {
    try {
      await applyOfficePreset();
      setStatus('Office preset applied.');
    } catch (error) {
      setStatus(`Endpoint tuning error: ${error.message}`);
    }
  };
}
if (resetEndpointTuningBtn) {
  resetEndpointTuningBtn.onclick = async () => {
    try {
      await resetEndpointTuning();
      setStatus('Endpoint tuning reset to defaults.');
    } catch (error) {
      setStatus(`Endpoint tuning error: ${error.message}`);
    }
  };
}

document.addEventListener('visibilitychange', async () => {
  if (document.visibilityState === 'visible' && wakeLockBtn.classList.contains('active') && !wakeLockSentinel) {
    try {
      await requestWakeLock();
    } catch (_) {
      updateWakeLockButton();
    }
  }
});

setStatus('Ready.');
updateAutoStopButton();
updateAutoContinueButton();
updateWakeLockButton();
setDebriefControls(false);
refreshEndpointStats();
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/service-worker.js').catch(() => {});
}
