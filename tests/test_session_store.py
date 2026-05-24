from pathlib import Path

from backend.session_store import DebriefSessionStore


class FixedClock:
    def now(self):
        return "2026-05-22T15:30:00"


def test_append_turns_and_save_final_markdown(tmp_path):
    store = DebriefSessionStore(root=tmp_path, clock=FixedClock())

    store.append_turn("debrief-test/session", "Bob", "We need to ship the bigger update.")
    store.append_turn("debrief-test/session", "Vicki", "Got it. Keep going.")
    result = store.save_final_summary(
        "debrief-test/session",
        "## Meeting Debrief\n\nSummary:\n- Bigger update captured.",
    )

    assert result.session_id == "debrief-testsession"
    assert result.markdown_path == tmp_path / "debriefs" / "2026-05-22-1530-debrief-testsession.md"
    assert result.transcript_path == tmp_path / "transcripts" / "debrief-testsession.md"
    assert result.markdown_path.exists()
    markdown = result.markdown_path.read_text(encoding="utf-8")
    assert markdown.startswith("# Debrief — 2026-05-22 15:30")
    assert "## Final Summary" in markdown
    assert "Bigger update captured." in markdown
    assert "## Raw Turns" in markdown
    assert "### Bob" in markdown
    assert "We need to ship the bigger update." in markdown


def test_final_markdown_filename_uses_title_from_summary(tmp_path):
    store = DebriefSessionStore(root=tmp_path, clock=FixedClock())

    result = store.save_final_summary(
        "debrief-abc123",
        "Title: Product Roadmap Update\n\n## Executive Summary\n- We expanded the update.",
    )

    assert result.title == "Product Roadmap Update"
    assert result.markdown_path == tmp_path / "debriefs" / "2026-05-22-1530-product-roadmap-update.md"
    assert "# Product Roadmap Update" in result.markdown_path.read_text(encoding="utf-8")


def test_final_markdown_can_be_saved_to_external_debrief_dir(tmp_path):
    external_dir = tmp_path / "Documents" / "Phone" / "debriefs"
    store = DebriefSessionStore(root=tmp_path / "app-data", debrief_dir=external_dir, clock=FixedClock())

    result = store.save_final_summary("road-update", "Summary:\n- Car test worked.")

    assert result.markdown_path == external_dir / "2026-05-22-1530-road-update.md"
    assert result.markdown_path.exists()
    assert result.transcript_path == tmp_path / "app-data" / "transcripts" / "road-update.md"


def test_session_ids_are_sanitized_and_bounded(tmp_path):
    store = DebriefSessionStore(root=tmp_path, clock=FixedClock())
    unsafe = "abc/../../" + "x" * 200

    result = store.append_turn(unsafe, "Bob", "hello")

    assert result.session_id == "abc" + "x" * 77
    assert result.transcript_path.parent == tmp_path / "transcripts"
    assert result.transcript_path.name == f"{result.session_id}.md"
