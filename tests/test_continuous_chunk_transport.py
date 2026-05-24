from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_frontend(name: str) -> str:
    return (ROOT / "frontend" / name).read_text(encoding="utf-8")


def test_continuous_chunk_js_flushes_turn_without_stopping_recorder():
    js = read_frontend("app.js")

    for expected in [
        "async function flushCurrentTurn",
        "mediaRecorder.requestData();",
        "mediaRecorder.pause();",
        "await flushCurrentTurn('Sending turn...');",
    ]:
        assert expected in js


def test_continuous_chunk_js_resumes_paused_recorder_for_next_turn():
    js = read_frontend("app.js")

    assert "else if (mediaRecorder.state === 'paused')" in js
    assert "mediaRecorder.resume();" in js
    assert "Pause + Send Turn" in js
