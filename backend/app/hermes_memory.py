from __future__ import annotations


def extract_memory_facts_from_transcript(transcript_text: str) -> list[str]:
    """Heuristic pre-alpha memory hook for stable facts.

    Keeps extraction intentionally small/safe until full Hermes integration.
    """
    text = (transcript_text or '').strip()
    if not text:
        return []

    facts: list[str] = []
    lowered = text.lower()

    if 'johnson' in lowered:
        facts.append('Client: Johnson family')

    if 'prefers text' in lowered or 'text updates' in lowered:
        facts.append('Preference: text updates')

    if 'by friday' in lowered or 'friday' in lowered:
        facts.append('Deadline mentioned: Friday')

    # de-dup while preserving order
    seen: set[str] = set()
    unique_facts: list[str] = []
    for fact in facts:
        if fact not in seen:
            seen.add(fact)
            unique_facts.append(fact)

    return unique_facts
