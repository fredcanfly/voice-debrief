from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_frontend(name: str) -> str:
    return (ROOT / "frontend" / name).read_text(encoding="utf-8")


def test_recording_js_reuses_a_single_mic_stream_between_turns():
    js = read_frontend("app.js")

    for expected in [
        "let micStream = null;",
        "async function getMicStream()",
        "const stream = await getMicStream();",
        "function releaseMicStream()",
        "releaseMicStream();",
    ]:
        assert expected in js


def test_recording_js_no_longer_stops_tracks_every_turn():
    js = read_frontend("app.js")

    assert "stream.getTracks().forEach(track => track.stop());" not in js
