from backend.prompts import FINAL_SUMMARY_REQUEST


def test_final_summary_prompt_requests_title_and_clean_sections():
    required_phrases = [
        "Title:",
        "Executive summary:",
        "What changed:",
        "Decisions:",
        "Action items:",
        "Risks / blockers:",
        "Open questions:",
        "Follow-ups:",
    ]

    for phrase in required_phrases:
        assert phrase in FINAL_SUMMARY_REQUEST

    assert "filename-safe title" in FINAL_SUMMARY_REQUEST
