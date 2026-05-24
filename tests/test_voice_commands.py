from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_frontend(name: str) -> str:
    return (ROOT / "frontend" / name).read_text(encoding="utf-8")


def test_voice_commands_include_full_utterance_stop_and_wrap_up_phrases():
    js = read_frontend("app.js")

    assert "VOICE_END_COMMANDS" in js
    for phrase in [
        "stop",
        "stop debrief",
        "end debrief",
        "wrap it up",
        "save this",
        "finish",
    ]:
        assert f"'{phrase}'" in js


def test_voice_command_detection_uses_exact_normalized_utterance_not_loose_keyword():
    js = read_frontend("app.js")

    assert "function normalizeVoiceCommand(text)" in js
    assert "function isEndDebriefVoiceCommand(text)" in js
    assert "VOICE_END_COMMANDS.has(normalizeVoiceCommand(text))" in js
    assert "includes('stop')" not in js


def test_audio_turn_routes_end_command_to_finalization_without_vicki_turn():
    js = read_frontend("app.js")

    assert "Voice command heard. Saving final notes..." in js
    assert "await finishDebrief();" in js
    command_check = "if (data.transcript_text && isEndDebriefVoiceCommand(data.transcript_text))"
    assert command_check in js

    command_index = js.index(command_check)
    first_vicki_after = js.index("addLog('Vicki'", command_index)
    finish_index = js.index("await finishDebrief();", command_index)
    assert finish_index < first_vicki_after


def test_end_button_reuses_finish_debrief_helper_and_does_not_auto_continue():
    js = read_frontend("app.js")

    assert "async function finishDebrief()" in js
    assert "endBtn.onclick = async () => {\n  await finishDebrief();\n};" in js
    finish_body = js[js.index("async function finishDebrief()"):js.index("copySummaryBtn.onclick")]
    assert "shouldAutoContinue()" not in finish_body
    assert "startRecordingTurn()" not in finish_body
