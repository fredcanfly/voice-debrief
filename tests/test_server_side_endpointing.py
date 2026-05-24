from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_backend(name: str) -> str:
    return (ROOT / "backend" / name).read_text(encoding="utf-8")


def read_frontend(name: str) -> str:
    return (ROOT / "frontend" / name).read_text(encoding="utf-8")


def test_backend_endpointing_has_noise_gate_and_response_flag():
    app_py = read_backend("app.py")

    for expected in [
        "def _is_endpoint_noise",
        "endpoint_min_speech_seconds",
        "endpoint_min_text_chars",
        "no_turn: bool = False",
        "endpoint_reason: str | None = None",
        "no_turn=True",
        "short_or_noisy_utterance",
    ]:
        assert expected in app_py


def test_frontend_handles_no_turn_without_agent_reply_cycle():
    js = read_frontend("app.js")

    for expected in [
        "if (data.no_turn)",
        "Heard a short/noisy turn. Keep going.",
        "if (shouldAutoContinue()) await startRecordingTurn();",
    ]:
        assert expected in js
