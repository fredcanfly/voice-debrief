let mediaRecorder = null;
let chunks = [];

const recordBtn = document.getElementById('recordBtn');
const stopBtn = document.getElementById('stopBtn');
const downloadBtn = document.getElementById('downloadBtn');
const sessionIdInput = document.getElementById('sessionId');
const statusEl = document.getElementById('status');
const resultEl = document.getElementById('result');

function setStatus(text, cls = '') {
  statusEl.textContent = text;
  statusEl.className = cls;
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
  setStatus('Recording...');
}

async function stopRecording() {
  if (!mediaRecorder || mediaRecorder.state !== 'recording') return;
  stopBtn.disabled = true;
  setStatus('Uploading...');
  mediaRecorder.stop();
}

async function uploadAudio(blob) {
  const form = new FormData();
  form.append('file', blob, 'pwa-recording.webm');

  try {
    const res = await fetch('/api/debrief/audio-upload', { method: 'POST', body: form });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    setStatus('Upload complete.', 'ok');
    resultEl.textContent = `upload_id=${data.upload_id} bytes=${data.bytes_received}`;
  } catch (error) {
    setStatus(`Upload failed: ${error.message}`, 'err');
  } finally {
    recordBtn.disabled = false;
    stopBtn.disabled = true;
  }
}

async function downloadLatestDebrief() {
  const sessionId = (sessionIdInput?.value || '').trim();
  if (!sessionId) {
    setStatus('Enter a session id before download.', 'err');
    return;
  }

  try {
    setStatus('Preparing download...');
    const response = await fetch(`/api/debrief/sessions/${encodeURIComponent(sessionId)}/document-download`);
    if (!response.ok) throw new Error(await response.text());

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);

    const disposition = response.headers.get('content-disposition') || '';
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const filename = match?.[1] || `${sessionId}-debrief.md`;

    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);

    setStatus('Download started.', 'ok');
  } catch (error) {
    setStatus(`Download failed: ${error.message}`, 'err');
  }
}

recordBtn.addEventListener('click', () => { startRecording().catch((e) => setStatus(`Mic error: ${e.message}`, 'err')); });
stopBtn.addEventListener('click', () => { stopRecording().catch((e) => setStatus(`Stop error: ${e.message}`, 'err')); });
downloadBtn.addEventListener('click', () => { downloadLatestDebrief().catch((e) => setStatus(`Download error: ${e.message}`, 'err')); });
