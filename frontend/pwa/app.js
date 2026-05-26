let mediaRecorder = null;
let chunks = [];

const recordBtn = document.getElementById('recordBtn');
const stopBtn = document.getElementById('stopBtn');
const statusEl = document.getElementById('status');
const resultEl = document.getElementById('result');
const accountNameEl = document.getElementById('accountName');
const logoutBtn = document.getElementById('logoutBtn');

const USER_ID_KEY = 'voiceDebrief.userId';
const FALLBACK_USER_ID = 'local-bob';

function resolveUserId() {
  const fromStorage = (window.localStorage?.getItem(USER_ID_KEY) || '').trim();
  return fromStorage || FALLBACK_USER_ID;
}

function setStatus(text, cls = '') {
  statusEl.textContent = text;
  statusEl.className = cls;
}

function setAccountInfo() {
  if (!accountNameEl) return;
  accountNameEl.textContent = resolveUserId();
}

async function startRecording() {
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    setStatus('Recording unavailable on this device/browser.', 'err');
    return;
  }

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  chunks = [];
  mediaRecorder = new MediaRecorder(stream);

  mediaRecorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) chunks.push(event.data);
  };

  mediaRecorder.onstop = async () => {
    const blob = new Blob(chunks, { type: mediaRecorder.mimeType || 'audio/webm' });
    stream.getTracks().forEach((t) => t.stop());
    await uploadAudio(blob);
  };

  mediaRecorder.start();
  recordBtn.disabled = true;
  stopBtn.disabled = false;
  setStatus('Recording…');
  resultEl.textContent = '';
}

async function stopRecording() {
  if (!mediaRecorder || mediaRecorder.state !== 'recording') return;
  stopBtn.disabled = true;
  setStatus('Uploading…');
  mediaRecorder.stop();
}

async function uploadAudio(blob) {
  const form = new FormData();
  form.append('file', blob, 'pwa-recording.webm');

  try {
    const headers = { 'x-user-id': resolveUserId() };
    const res = await fetch('/api/debrief/audio-upload', { method: 'POST', body: form, headers });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    setStatus('Upload complete.', 'ok');
    resultEl.textContent = `Upload ID: ${data.upload_id} • Bytes: ${data.bytes_received}`;
  } catch (error) {
    setStatus(`Upload failed: ${error.message}`, 'err');
  } finally {
    recordBtn.disabled = false;
    stopBtn.disabled = true;
  }
}

recordBtn.addEventListener('click', () => {
  startRecording().catch((e) => setStatus(`Mic error: ${e.message}`, 'err'));
});

stopBtn.addEventListener('click', () => {
  stopRecording().catch((e) => setStatus(`Stop error: ${e.message}`, 'err'));
});

setAccountInfo();

if (!window.localStorage?.getItem(USER_ID_KEY)) {
  window.location.href = '/login';
}

if (logoutBtn) {
  logoutBtn.addEventListener('click', () => {
    window.localStorage?.removeItem(USER_ID_KEY);
    window.location.href = '/login';
  });
}
