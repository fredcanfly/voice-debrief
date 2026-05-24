from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_backend(name: str) -> str:
    return (ROOT / "backend" / name).read_text(encoding="utf-8")


def read_frontend(name: str) -> str:
    return (ROOT / "frontend" / name).read_text(encoding="utf-8")


def test_backend_has_endpoint_stats_route_and_threshold_snapshot():
    app_py = read_backend("app.py")

    for expected in [
        "@app.get('/api/debug/endpoint-stats')",
        "def endpoint_stats()",
        "'accepted_turns'",
        "'filtered_turns'",
        "'filtered_rate'",
        "'thresholds'",
        "'endpoint_min_speech_seconds'",
        "'endpoint_min_text_chars'",
        "'whisper_vad_min_silence_ms'",
    ]:
        assert expected in app_py


def test_backend_increments_endpoint_stats_in_audio_flow():
    app_py = read_backend("app.py")

    for expected in [
        "_endpoint_stats['filtered_turns'] += 1",
        "_endpoint_stats['accepted_turns'] += 1",
        "_endpoint_stats['filtered_events'].append",
        "speech_seconds",
        "text_chars",
    ]:
        assert expected in app_py


def test_backend_has_threshold_update_route():
    app_py = read_backend("app.py")

    for expected in [
        "class EndpointThresholdsUpdate(BaseModel)",
        "@app.post('/api/debug/endpoint-thresholds')",
        "def update_endpoint_thresholds",
        "settings.endpoint_min_speech_seconds",
        "settings.endpoint_min_text_chars",
        "settings.whisper_vad_min_silence_ms",
    ]:
        assert expected in app_py


def test_backend_persists_endpoint_thresholds_to_disk():
    app_py = read_backend("app.py")

    for expected in [
        "ENDPOINT_TUNING_PATH",
        "endpoint_tuning.json",
        "def _save_endpoint_thresholds",
        "def _load_endpoint_thresholds",
        "json.dumps",
        "json.loads",
        "_save_endpoint_thresholds()",
    ]:
        assert expected in app_py


def test_backend_has_threshold_validation_and_presets_and_reset():
    app_py = read_backend("app.py")

    for expected in [
        "def _validate_thresholds",
        "HTTPException(status_code=400",
        "preset: str | None = None",
        "if req.preset == 'driving'",
        "if req.preset == 'office'",
        "if req.reset_to_defaults",
        "DEFAULT_ENDPOINT_THRESHOLDS",
    ]:
        assert expected in app_py


def test_frontend_reads_and_displays_endpoint_stats():
    js = read_frontend("app.js")

    for expected in [
        "'/api/debug/endpoint-stats'",
        "refreshEndpointStats",
        "endpointStats",
        "endpointThresholds",
    ]:
        assert expected in js


def test_frontend_can_apply_endpoint_threshold_updates():
    js = read_frontend("app.js")
    html = read_frontend("index.html")

    for expected in [
        "endpointMinSpeech",
        "endpointMinChars",
        "endpointVadSilence",
        "applyEndpointTuning",
        "'/api/debug/endpoint-thresholds'",
    ]:
        assert expected in js or expected in html


def test_frontend_has_reset_and_preset_controls():
    js = read_frontend("app.js")
    html = read_frontend("index.html")

    for expected in [
        "applyDrivingPreset",
        "applyOfficePreset",
        "resetEndpointTuning",
        "resetEndpointTuningBtn",
        "applyEndpointPreset('driving')",
        "applyEndpointPreset('office')",
    ]:
        assert expected in js or expected in html
