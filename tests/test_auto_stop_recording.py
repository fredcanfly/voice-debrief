from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_frontend(name: str) -> str:
    return (ROOT / "frontend" / name).read_text(encoding="utf-8")


def test_auto_stop_html_exposes_hands_free_toggle_and_state():
    html = read_frontend("index.html")

    assert 'id="autoStop"' in html
    assert 'id="autoStopState"' in html
    assert 'Silence Auto-Stop' in html
    assert 'hands-free-card' in html

    auto_stop_index = html.index('id="autoStop"')
    advanced_index = html.index('class="advanced-tests"')
    assert auto_stop_index < advanced_index


def test_auto_stop_css_makes_toggle_touch_friendly_and_visible():
    css = read_frontend("styles.css")

    assert ".hands-free-card" in css
    assert ".auto-stop-row" in css
    assert ".auto-stop-button.active" in css
    assert "min-height: 72px" in css


def test_auto_stop_js_detects_silence_and_stops_recording():
    js = read_frontend("app.js")

    for expected in [
        "autoStopEnabled",
        "silenceStartedAt",
        "AUTO_STOP_SILENCE_MS",
        "AUTO_STOP_GRACE_MS",
        "createAnalyser",
        "requestAnimationFrame(monitorSilence)",
        "mediaRecorder.stop()",
        "Silence detected. Sending turn...",
        "Listening again. Start talking.",
    ]:
        assert expected in js
