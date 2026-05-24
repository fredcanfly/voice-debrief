from __future__ import annotations


def extract_skill_hints_from_transcript(transcript_text: str) -> list[str]:
    """Pre-alpha heuristic skill hints for conversational behavior."""
    text = (transcript_text or '').strip().lower()
    if not text:
        return []

    hints: list[str] = []

    if 'sensitive' in text or 'emotional' in text:
        hints.append('Sensitive topic handling: start gently')

    if 'conflict' in text or 'tension' in text:
        hints.append('Relational tension: ask neutral clarifying question')

    if 'urgent' in text or 'asap' in text:
        hints.append('Urgency: confirm owner and deadline explicitly')

    seen: set[str] = set()
    unique: list[str] = []
    for hint in hints:
        if hint not in seen:
            seen.add(hint)
            unique.append(hint)
    return unique
