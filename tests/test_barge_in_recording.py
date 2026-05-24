from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_frontend(name: str) -> str:
    return (ROOT / "frontend" / name).read_text(encoding="utf-8")


def test_barge_in_js_tracks_active_playback_and_can_stop_it():
    js = read_frontend("app.js")

    for expected in [
        "let currentPlaybackAudio = null;",
        "function stopPlayback(reason = 'Playback stopped.')",
        "audio.pause();",
        "audio.currentTime = 0;",
    ]:
        assert expected in js


def test_barge_in_js_interrupts_tts_when_starting_recording_turn():
    js = read_frontend("app.js")

    assert "stopPlayback('Interrupted Vicki. Listening now...');" in js
    assert "setStatus('Vicki speaking. Tap Record to interrupt.');" in js
