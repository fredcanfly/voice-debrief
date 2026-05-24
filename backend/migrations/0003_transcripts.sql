CREATE TABLE IF NOT EXISTS debrief_transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    transcript_text TEXT NOT NULL,
    stt_model TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(session_id) REFERENCES debrief_sessions(session_id)
);
