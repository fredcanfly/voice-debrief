from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import shutil
from collections import deque
import json

from fastapi import Depends, FastAPI, File, HTTPException, Header, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .beta_auth import AuthUser, auth_user_from_headers, can_signup
from .config import get_settings
from .hermes_client import HermesClient
from .session_store import DebriefSessionStore
from .stt_local import LocalWhisperSTT
from .tts_edge import EdgeTTS

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data'
AUDIO_DIR = DATA_DIR / 'audio'
UPLOAD_DIR = DATA_DIR / 'uploads'
TRANSCRIPT_DIR = DATA_DIR / 'transcripts'
DEBRIEF_DIR = DATA_DIR / 'debriefs'
FRONTEND_DIR = ROOT / 'frontend'
ENDPOINT_TUNING_PATH = DATA_DIR / 'endpoint_tuning.json'
USER_SETTINGS_PATH = DATA_DIR / 'user_settings.json'
BETA_PROFILES_PATH = DATA_DIR / 'beta_profiles.json'
for directory in (AUDIO_DIR, UPLOAD_DIR, TRANSCRIPT_DIR, DEBRIEF_DIR):
    directory.mkdir(parents=True, exist_ok=True)

settings = get_settings()
settings.debrief_output_dir.mkdir(parents=True, exist_ok=True)
app = FastAPI(title='Vicki Voice Debrief Bridge')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.mount('/audio', StaticFiles(directory=str(AUDIO_DIR)), name='audio')
app.mount('/debriefs', StaticFiles(directory=str(settings.debrief_output_dir)), name='debriefs')
app.mount('/static', StaticFiles(directory=str(FRONTEND_DIR)), name='static')

hermes = HermesClient(settings)
tts = EdgeTTS(settings.edge_tts_voice, AUDIO_DIR)
stt = LocalWhisperSTT(settings)
session_store = DebriefSessionStore(DATA_DIR, debrief_dir=settings.debrief_output_dir)

DEFAULT_ENDPOINT_THRESHOLDS = {
    'endpoint_min_speech_seconds': 0.55,
    'endpoint_min_text_chars': 8,
    'whisper_vad_min_silence_ms': 700,
}

DRIVING_ENDPOINT_PRESET = {
    'endpoint_min_speech_seconds': 0.75,
    'endpoint_min_text_chars': 12,
    'whisper_vad_min_silence_ms': 900,
}

OFFICE_ENDPOINT_PRESET = {
    'endpoint_min_speech_seconds': 0.45,
    'endpoint_min_text_chars': 6,
    'whisper_vad_min_silence_ms': 600,
}

_endpoint_stats = {
    'accepted_turns': 0,
    'filtered_turns': 0,
    'filtered_events': deque(maxlen=50),
}


def _read_json_file(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def _write_json_file(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def _get_auth_user(
    authorization: str | None = Header(default=None),
    x_dev_user_id: str | None = Header(default=None),
    x_dev_user_email: str | None = Header(default=None),
) -> AuthUser:
    return auth_user_from_headers(settings, authorization, x_dev_user_id, x_dev_user_email)


def _default_user_settings() -> dict:
    return {
        'voice_name': settings.edge_tts_voice,
        'endpoint_min_speech_seconds': settings.endpoint_min_speech_seconds,
        'endpoint_min_text_chars': settings.endpoint_min_text_chars,
        'vad_silence_ms': settings.whisper_vad_min_silence_ms,
        'setup_complete': False,
    }


def _save_endpoint_thresholds() -> None:
    payload = {
        'endpoint_min_speech_seconds': settings.endpoint_min_speech_seconds,
        'endpoint_min_text_chars': settings.endpoint_min_text_chars,
        'whisper_vad_min_silence_ms': settings.whisper_vad_min_silence_ms,
    }
    ENDPOINT_TUNING_PATH.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def _validate_thresholds() -> None:
    if settings.endpoint_min_speech_seconds < 0 or settings.endpoint_min_speech_seconds > 5:
        raise HTTPException(status_code=400, detail='endpoint_min_speech_seconds must be between 0 and 5')
    if settings.endpoint_min_text_chars < 0 or settings.endpoint_min_text_chars > 120:
        raise HTTPException(status_code=400, detail='endpoint_min_text_chars must be between 0 and 120')
    if settings.whisper_vad_min_silence_ms < 0 or settings.whisper_vad_min_silence_ms > 5000:
        raise HTTPException(status_code=400, detail='whisper_vad_min_silence_ms must be between 0 and 5000')


def _apply_threshold_values(values: dict[str, float | int]) -> None:
    settings.endpoint_min_speech_seconds = max(0.0, float(values['endpoint_min_speech_seconds']))
    settings.endpoint_min_text_chars = max(0, int(values['endpoint_min_text_chars']))
    settings.whisper_vad_min_silence_ms = max(0, int(values['whisper_vad_min_silence_ms']))


def _load_endpoint_thresholds() -> None:
    if not ENDPOINT_TUNING_PATH.exists():
        return
    try:
        payload = json.loads(ENDPOINT_TUNING_PATH.read_text(encoding='utf-8'))
    except Exception:
        return
    if 'endpoint_min_speech_seconds' in payload:
        settings.endpoint_min_speech_seconds = max(0.0, float(payload['endpoint_min_speech_seconds']))
    if 'endpoint_min_text_chars' in payload:
        settings.endpoint_min_text_chars = max(0, int(payload['endpoint_min_text_chars']))
    if 'whisper_vad_min_silence_ms' in payload:
        settings.whisper_vad_min_silence_ms = max(0, int(payload['whisper_vad_min_silence_ms']))
    _validate_thresholds()


_load_endpoint_thresholds()


class StartRequest(BaseModel):
    session_id: str | None = None


class MessageRequest(BaseModel):
    session_id: str
    text: str
    speak: bool = True


class DebriefResponse(BaseModel):
    session_id: str
    reply_text: str
    audio_url: str | None = None
    transcript_text: str | None = None
    final_markdown_url: str | None = None
    final_title: str | None = None
    no_turn: bool = False
    endpoint_reason: str | None = None


class EndpointThresholdsUpdate(BaseModel):
    endpoint_min_speech_seconds: float | None = None
    endpoint_min_text_chars: int | None = None
    whisper_vad_min_silence_ms: int | None = None
    preset: str | None = None
    reset_to_defaults: bool = False


class UserSettingsUpdate(BaseModel):
    voice_name: str | None = None
    endpoint_min_speech_seconds: float | None = None
    endpoint_min_text_chars: int | None = None
    vad_silence_ms: int | None = None
    setup_complete: bool | None = None


@app.get('/api/beta/can-signup')
async def beta_can_signup(email: str | None = None, user: AuthUser = Depends(_get_auth_user)):
    profiles = _read_json_file(BETA_PROFILES_PATH, {'users': []})
    existing_ids = [row.get('user_id', '') for row in profiles.get('users', []) if row.get('user_id')]
    allowed, reason = can_signup(
        settings=settings,
        existing_user_ids=existing_ids,
        email=email or user.email,
        requesting_user_id=user.user_id,
    )
    return {'allowed': allowed, 'reason': reason, 'max_beta_users': settings.max_beta_users}


@app.get('/api/me/settings')
async def get_my_settings(user: AuthUser = Depends(_get_auth_user)):
    data = _read_json_file(USER_SETTINGS_PATH, {'users': {}})
    users = data.get('users', {})
    payload = users.get(user.user_id) or _default_user_settings()
    return {'user_id': user.user_id, 'settings': payload}


@app.post('/api/me/settings')
async def update_my_settings(req: UserSettingsUpdate, user: AuthUser = Depends(_get_auth_user)):
    data = _read_json_file(USER_SETTINGS_PATH, {'users': {}})
    users = data.setdefault('users', {})
    current = users.get(user.user_id) or _default_user_settings()

    if req.voice_name is not None:
        current['voice_name'] = req.voice_name
    if req.endpoint_min_speech_seconds is not None:
        current['endpoint_min_speech_seconds'] = float(req.endpoint_min_speech_seconds)
    if req.endpoint_min_text_chars is not None:
        current['endpoint_min_text_chars'] = int(req.endpoint_min_text_chars)
    if req.vad_silence_ms is not None:
        current['vad_silence_ms'] = int(req.vad_silence_ms)
    if req.setup_complete is not None:
        current['setup_complete'] = bool(req.setup_complete)

    users[user.user_id] = current
    _write_json_file(USER_SETTINGS_PATH, data)

    profiles = _read_json_file(BETA_PROFILES_PATH, {'users': []})
    known = {row.get('user_id') for row in profiles.get('users', [])}
    if user.user_id not in known:
        profiles.setdefault('users', []).append({'user_id': user.user_id, 'email': user.email})
        _write_json_file(BETA_PROFILES_PATH, profiles)

    return {'user_id': user.user_id, 'settings': current}


@app.get('/')
async def index():
    return FileResponse(FRONTEND_DIR / 'index.html')


@app.get('/api/health')
async def health():
    hermes_health = None
    hermes_error = None
    try:
        hermes_health = await hermes.health()
    except Exception as exc:  # health should explain dependency issues, not crash
        hermes_error = str(exc)
    return {
        'ok': True,
        'settings': {
            'hermes_api_base': settings.hermes_api_base,
            'stt_provider': settings.stt_provider,
            'whisper_model': settings.whisper_model,
            'whisper_device': settings.whisper_device,
            'whisper_compute_type': settings.whisper_compute_type,
            'edge_tts_voice': settings.edge_tts_voice,
        },
        'hermes': hermes_health,
        'hermes_error': hermes_error,
    }


@app.get('/api/debug/endpoint-stats')
async def endpoint_stats():
    accepted_turns = int(_endpoint_stats['accepted_turns'])
    filtered_turns = int(_endpoint_stats['filtered_turns'])
    total_turns = accepted_turns + filtered_turns
    filtered_rate = round((filtered_turns / total_turns), 3) if total_turns else 0.0
    return {
        'accepted_turns': accepted_turns,
        'filtered_turns': filtered_turns,
        'total_turns': total_turns,
        'filtered_rate': filtered_rate,
        'thresholds': {
            'endpoint_min_speech_seconds': settings.endpoint_min_speech_seconds,
            'endpoint_min_text_chars': settings.endpoint_min_text_chars,
            'whisper_vad_min_silence_ms': settings.whisper_vad_min_silence_ms,
        },
        'recent_filtered_events': list(_endpoint_stats['filtered_events']),
    }


@app.post('/api/debug/endpoint-thresholds')
async def update_endpoint_thresholds(req: EndpointThresholdsUpdate):
    old_values = {
        'endpoint_min_speech_seconds': settings.endpoint_min_speech_seconds,
        'endpoint_min_text_chars': settings.endpoint_min_text_chars,
        'whisper_vad_min_silence_ms': settings.whisper_vad_min_silence_ms,
    }

    try:
        if req.reset_to_defaults:
            _apply_threshold_values(DEFAULT_ENDPOINT_THRESHOLDS)
        if req.preset == 'driving':
            _apply_threshold_values(DRIVING_ENDPOINT_PRESET)
        if req.preset == 'office':
            _apply_threshold_values(OFFICE_ENDPOINT_PRESET)

        if req.endpoint_min_speech_seconds is not None:
            settings.endpoint_min_speech_seconds = float(req.endpoint_min_speech_seconds)
        if req.endpoint_min_text_chars is not None:
            settings.endpoint_min_text_chars = int(req.endpoint_min_text_chars)
        if req.whisper_vad_min_silence_ms is not None:
            settings.whisper_vad_min_silence_ms = int(req.whisper_vad_min_silence_ms)

        _validate_thresholds()
    except HTTPException:
        _apply_threshold_values(old_values)
        raise

    _save_endpoint_thresholds()
    return await endpoint_stats()


@app.post('/api/debrief/start')
async def start_debrief(req: StartRequest) -> dict[str, str]:
    session_id = req.session_id or f"debrief-{uuid4().hex[:12]}"
    return {'session_id': session_id, 'message': 'Debrief started.'}


@app.post('/api/debrief/message', response_model=DebriefResponse)
async def debrief_message(req: MessageRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail='text is required')
    reply = await hermes.send_debrief_turn(req.session_id, req.text.strip())
    audio_url = await _maybe_speak(reply.text, req.speak)
    session_store.append_turn(req.session_id, speaker='Bob', text=req.text.strip())
    session_store.append_turn(req.session_id, speaker='Vicki', text=reply.text)
    return DebriefResponse(session_id=req.session_id, reply_text=reply.text, audio_url=audio_url)


@app.post('/api/debrief/end', response_model=DebriefResponse)
async def end_debrief(req: MessageRequest):
    reply = await hermes.end_debrief(req.session_id)
    audio_url = await _maybe_speak('Debrief saved. I made final notes for review.', req.speak)
    saved = session_store.save_final_summary(req.session_id, reply.text)
    final_markdown_url = f"/debriefs/{saved.markdown_path.name}" if saved.markdown_path else None
    return DebriefResponse(
        session_id=saved.session_id,
        reply_text=reply.text,
        audio_url=audio_url,
        final_markdown_url=final_markdown_url,
        final_title=saved.title,
    )


@app.post('/api/transcribe')
async def transcribe(file: UploadFile = File(...)):
    suffix = Path(file.filename or 'audio.webm').suffix or '.webm'
    out = UPLOAD_DIR / f"upload-{uuid4().hex}{suffix}"
    with out.open('wb') as handle:
        shutil.copyfileobj(file.file, handle)
    return stt.transcribe_file(out)


@app.post('/api/debrief/audio', response_model=DebriefResponse)
async def debrief_audio(session_id: str, file: UploadFile = File(...), speak: bool = True):
    suffix = Path(file.filename or 'audio.webm').suffix or '.webm'
    out = UPLOAD_DIR / f"turn-{uuid4().hex}{suffix}"
    with out.open('wb') as handle:
        shutil.copyfileobj(file.file, handle)
    transcript = stt.transcribe_file(out)
    text = transcript['text']
    if not text:
        raise HTTPException(status_code=400, detail='No speech detected')
    if _is_endpoint_noise(transcript):
        text_chars = len(text)
        speech_seconds = float(transcript.get('speech_seconds') or 0.0)
        _endpoint_stats['filtered_turns'] += 1
        _endpoint_stats['filtered_events'].append(
            {
                'session_id': session_id,
                'endpoint_reason': 'short_or_noisy_utterance',
                'speech_seconds': round(speech_seconds, 3),
                'text_chars': text_chars,
            }
        )
        return DebriefResponse(
            session_id=session_id,
            reply_text='',
            transcript_text=text,
            no_turn=True,
            endpoint_reason='short_or_noisy_utterance',
        )
    reply = await hermes.send_debrief_turn(session_id, text)
    _endpoint_stats['accepted_turns'] += 1
    audio_url = await _maybe_speak(reply.text, speak)
    session_store.append_turn(session_id, speaker='Bob', text=text)
    session_store.append_turn(session_id, speaker='Vicki', text=reply.text)
    return DebriefResponse(session_id=session_id, reply_text=reply.text, audio_url=audio_url, transcript_text=text)


def _is_endpoint_noise(transcript: dict[str, object]) -> bool:
    text = str(transcript.get('text') or '').strip()
    speech_seconds = float(transcript.get('speech_seconds') or 0.0)
    return speech_seconds < settings.endpoint_min_speech_seconds and len(text) < settings.endpoint_min_text_chars


def _reset_endpoint_stats() -> None:
    _endpoint_stats['accepted_turns'] = 0
    _endpoint_stats['filtered_turns'] = 0
    _endpoint_stats['filtered_events'].clear()


async def _maybe_speak(text: str, speak: bool) -> str | None:
    if not speak or not text:
        return None
    audio_path = await tts.synthesize(text)
    return f"/audio/{audio_path.name}"
