from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import edge_tts


class EdgeTTS:
    def __init__(self, voice: str, audio_dir: Path):
        self.voice = voice
        self.audio_dir = audio_dir
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    async def synthesize(self, text: str) -> Path:
        out = self.audio_dir / f"reply-{uuid4().hex}.mp3"
        communicate = edge_tts.Communicate(text=text, voice=self.voice)
        await communicate.save(str(out))
        return out
