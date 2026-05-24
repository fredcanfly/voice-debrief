from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import httpx


class KokoroTTSError(RuntimeError):
    pass


def synthesize_kokoro_tts(*, text: str, out_dir: Path | None = None) -> Path:
    base_url = (os.getenv('KOKORO_BASE_URL') or 'http://127.0.0.1:8880').rstrip('/')
    voice = os.getenv('KOKORO_VOICE') or 'af_sarah'
    audio_format = (os.getenv('KOKORO_FORMAT') or 'wav').lower()

    target_dir = out_dir or Path(__file__).resolve().parents[2] / 'data' / 'audio'
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = target_dir / f'followup-{uuid4().hex}.{audio_format}'

    payload = {
        'model': 'kokoro',
        'input': text,
        'voice': voice,
        'response_format': audio_format,
        'stream': False,
    }
    response = httpx.post(f'{base_url}/v1/audio/speech', json=payload, timeout=90)
    if response.status_code >= 400:
        raise KokoroTTSError(f'Kokoro TTS error {response.status_code}: {response.text}')

    if not response.content:
        raise KokoroTTSError('Kokoro TTS returned empty audio payload')

    output_path.write_bytes(response.content)
    return output_path
