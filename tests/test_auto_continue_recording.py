from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_frontend(name: str) -> str:
    return (ROOT / "frontend" / name).read_text(encoding="utf-8")


def test_auto_continue_html_exposes_toggle_before_advanced_controls():
    html = read_frontend("index.html")

    assert 'id="autoContinue"' in html
    assert 'id="autoContinueState"' in html
    assert 'Hands-Free Continue' in html

    auto_continue_index = html.index('id="autoContinue"')
    advanced_index = html.index('class="advanced-tests"')
    assert auto_continue_index < advanced_index


def test_auto_continue_css_has_active_touch_target():
    css = read_frontend("styles.css")

    assert ".auto-continue-button" in css
    assert ".auto-continue-button.active" in css
    assert ".hands-free-options" in css


def test_auto_continue_js_rearms_recording_after_vicki_audio_finishes():
    js = read_frontend("app.js")

    for expected in [
        "autoContinueEnabled",
        "startRecordingTurn",
        "shouldAutoContinue()",
        "Auto-continue on. I’ll reopen the mic after Vicki replies.",
        "Listening again. Start talking.",
        "await playAudio(data.audio_url);\n    if (shouldAutoContinue()) await startRecordingTurn();",
    ]:
        assert expected in js


def test_auto_continue_js_does_not_rearm_after_final_debrief():
    js = read_frontend("app.js")

    end_handler = js[js.index("\nendBtn.onclick = async"):]
    assert "shouldAutoContinue()" not in end_handler
    assert "startRecordingTurn()" not in end_handler
