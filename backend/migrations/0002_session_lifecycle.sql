ALTER TABLE debrief_sessions ADD COLUMN status TEXT NOT NULL DEFAULT 'created';
ALTER TABLE debrief_sessions ADD COLUMN started_at TEXT;
ALTER TABLE debrief_sessions ADD COLUMN ended_at TEXT;
