from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol
import re


class Clock(Protocol):
    def now(self) -> str:
        ...


class SystemClock:
    def now(self) -> str:
        return datetime.now().isoformat(timespec="seconds")


@dataclass(frozen=True)
class SessionWriteResult:
    session_id: str
    transcript_path: Path
    markdown_path: Path | None = None
    title: str | None = None


class DebriefSessionStore:
    def __init__(self, root: Path, debrief_dir: Path | None = None, clock: Clock | None = None):
        self.root = root
        self.clock = clock or SystemClock()
        self.transcript_dir = root / "transcripts"
        self.debrief_dir = debrief_dir or root / "debriefs"
        self.transcript_dir.mkdir(parents=True, exist_ok=True)
        self.debrief_dir.mkdir(parents=True, exist_ok=True)

    def append_turn(self, session_id: str, speaker: str, text: str) -> SessionWriteResult:
        safe_session = self.safe_session_id(session_id)
        transcript_path = self.transcript_path(safe_session)
        with transcript_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n### {speaker}\n\n{text.strip()}\n")
        return SessionWriteResult(session_id=safe_session, transcript_path=transcript_path)

    def save_final_summary(self, session_id: str, summary: str) -> SessionWriteResult:
        safe_session = self.safe_session_id(session_id)
        transcript_path = self.transcript_path(safe_session)
        transcript = ""
        if transcript_path.exists():
            transcript = transcript_path.read_text(encoding="utf-8").strip()
        title = self.extract_title(summary)
        cleaned_summary = self.strip_title_line(summary)
        self.append_turn(safe_session, "Final summary", summary)
        markdown_path = self.debrief_path(safe_session, title=title)
        markdown_path.write_text(
            self._format_final_markdown(summary=cleaned_summary, raw_turns=transcript, title=title),
            encoding="utf-8",
        )
        return SessionWriteResult(
            session_id=safe_session,
            transcript_path=transcript_path,
            markdown_path=markdown_path,
            title=title,
        )

    def transcript_path(self, session_id: str) -> Path:
        return self.transcript_dir / f"{self.safe_session_id(session_id)}.md"

    def debrief_path(self, session_id: str, title: str | None = None) -> Path:
        safe_session = self.safe_session_id(session_id)
        stamp = self._timestamp_slug()
        name_slug = self.title_slug(title) if title else safe_session
        return self.debrief_dir / f"{stamp}-{name_slug}.md"

    def safe_session_id(self, session_id: str) -> str:
        safe = "".join(ch for ch in session_id if ch.isalnum() or ch in {"-", "_"})[:80]
        return safe or "debrief"

    def _format_final_markdown(self, summary: str, raw_turns: str, title: str | None = None) -> str:
        display_time = self._display_timestamp()
        raw = raw_turns or "None captured."
        heading = title or f"Debrief — {display_time}"
        return (
            f"# {heading}\n\n"
            f"Date: {display_time}\n\n"
            f"## Final Summary\n\n"
            f"{summary.strip()}\n\n"
            f"## Raw Turns\n\n"
            f"{raw}\n"
        )

    def extract_title(self, summary: str) -> str | None:
        for line in summary.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            title_match = re.match(r"^(?:#+\s*)?Title:\s*(.+)$", stripped, flags=re.IGNORECASE)
            if title_match:
                return self._clean_title(title_match.group(1))
            heading_match = re.match(r"^#\s+(.+)$", stripped)
            if heading_match:
                return self._clean_title(heading_match.group(1))
            break
        return None

    def strip_title_line(self, summary: str) -> str:
        lines = summary.splitlines()
        if not lines:
            return summary
        first_content_index = next((index for index, line in enumerate(lines) if line.strip()), None)
        if first_content_index is None:
            return ""
        first = lines[first_content_index].strip()
        if re.match(r"^(?:#+\s*)?Title:\s*.+$", first, flags=re.IGNORECASE) or re.match(r"^#\s+.+$", first):
            del lines[first_content_index]
        return "\n".join(lines).strip()

    def title_slug(self, title: str) -> str:
        cleaned = self._clean_title(title).lower()
        slug = re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-")
        return slug[:80].strip("-") or "debrief"

    def _clean_title(self, title: str) -> str:
        cleaned = re.sub(r"[*_`#]", "", title).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned[:120].strip()

    def _now(self) -> datetime:
        value = self.clock.now()
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    def _timestamp_slug(self) -> str:
        return self._now().strftime("%Y-%m-%d-%H%M")

    def _display_timestamp(self) -> str:
        return self._now().strftime("%Y-%m-%d %H:%M")
