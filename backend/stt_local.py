from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Any

from faster_whisper import WhisperModel

from .config import Settings


@lru_cache(maxsize=1)
def _load_model(model_name: str, device: str, compute_type: str) -> WhisperModel:
    return WhisperModel(model_name, device=device, compute_type=compute_type)


class LocalWhisperSTT:
    def __init__(self, settings: Settings):
        self.settings = settings

    def transcribe_file(self, audio_path: Path) -> dict[str, Any]:
        started = perf_counter()
        model = _load_model(
            self.settings.whisper_model,
            self.settings.whisper_device,
            self.settings.whisper_compute_type,
        )
        segments, info = model.transcribe(
            str(audio_path),
            language=self.settings.whisper_language or None,
            vad_filter=True,
            vad_parameters={'min_silence_duration_ms': self.settings.whisper_vad_min_silence_ms},
            beam_size=5,
        )
        segment_list = [
            {'start': round(seg.start, 2), 'end': round(seg.end, 2), 'text': seg.text.strip()}
            for seg in segments
        ]
        speech_seconds = round(
            sum(max(0.0, (s['end'] - s['start'])) for s in segment_list if s['text']),
            3,
        )
        text = ' '.join(s['text'] for s in segment_list).strip()
        return {
            'text': text,
            'segments': segment_list,
            'segment_count': len(segment_list),
            'speech_seconds': speech_seconds,
            'duration_seconds': getattr(info, 'duration', None),
            'language': getattr(info, 'language', None),
            'language_probability': getattr(info, 'language_probability', None),
            'elapsed_seconds': round(perf_counter() - started, 3),
            'model': self.settings.whisper_model,
            'device': self.settings.whisper_device,
            'compute_type': self.settings.whisper_compute_type,
        }
