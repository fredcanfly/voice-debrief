from __future__ import annotations

from pathlib import Path
import os
import httpx


class OpenAITranscriptionError(RuntimeError):
    pass


def transcribe_file_openai(audio_path: Path, api_key: str | None = None, model: str | None = None) -> dict:
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise OpenAITranscriptionError("OPENAI_API_KEY is not set")

    stt_model = model or os.getenv("OPENAI_STT_MODEL") or "gpt-4o-mini-transcribe"

    with audio_path.open("rb") as f:
        files = {"file": (audio_path.name, f, "audio/webm")}
        data = {"model": stt_model}
        headers = {"Authorization": f"Bearer {key}"}
        response = httpx.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers=headers,
            data=data,
            files=files,
            timeout=60,
        )

    if response.status_code >= 400:
        raise OpenAITranscriptionError(f"OpenAI STT error {response.status_code}: {response.text}")

    payload = response.json()
    text = payload.get("text", "").strip()
    return {
        "text": text,
        "model": stt_model,
        "raw": payload,
    }
