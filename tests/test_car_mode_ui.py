from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_frontend(name: str) -> str:
    return (ROOT / "frontend" / name).read_text(encoding="utf-8")


def test_car_mode_html_prioritizes_driving_controls():
    html = read_frontend("index.html")

    assert 'class="hero-status"' in html
    assert 'id="wakeLock"' in html
    assert 'class="car-controls"' in html
    assert 'class="advanced-tests"' in html
    assert '<summary>Advanced testing controls</summary>' in html

    record_index = html.index('id="record"')
    end_index = html.index('id="end"')
    advanced_index = html.index('class="advanced-tests"')
    assert record_index < advanced_index
    assert end_index < advanced_index


def test_car_mode_css_makes_primary_buttons_large_and_touch_friendly():
    css = read_frontend("styles.css")

    assert ".car-controls" in css
    assert "min-height: 150px" in css
    assert "font-size: clamp(1.6rem" in css
    assert ".hero-status" in css
    assert "position: sticky" in css


def test_car_mode_js_uses_wake_lock_and_clear_state_labels():
    js = read_frontend("app.js")

    assert "wakeLockSentinel" in js
    assert "navigator.wakeLock.request('screen')" in js
    for state in [
        "Ready.",
        "Recording. Tap Stop when done.",
        "Transcribing audio locally...",
        "Vicki is thinking...",
        "Saving final notes...",
        "Debrief saved",
    ]:
        assert state in js
