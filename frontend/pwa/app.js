let mediaRecorder = null;
let chunks = [];

const recordBtn = document.getElementById('recordBtn');
const stopBtn = document.getElementById('stopBtn');
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

recordBtn.addEventListener('click', () => { startRecording().catch((e) => setStatus(`Mic error: ${e.message}`, 'err')); });
stopBtn.addEventListener('click', () => { stopRecording().catch((e) => setStatus(`Stop error: ${e.message}`, 'err')); });
