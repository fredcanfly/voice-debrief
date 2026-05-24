from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .db import create_session, get_session, init_sqlite, set_session_ended, set_session_started
from .models import SessionCreateResponse, SessionStatusResponse

ROOT = Path(__file__).resolve().parents[2]
PWA_DIR = ROOT / "frontend" / "pwa"
DB_PATH = ROOT / "data" / "voice_debrief.sqlite3"


class SessionCreateRequest(BaseModel):
    session_id: str | None = None


def create_app() -> FastAPI:
    app = FastAPI(title="Voice Debrief Assistant API")
    init_sqlite(DB_PATH)

    app.mount("/pwa", StaticFiles(directory=str(PWA_DIR)), name="pwa")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "voice-debrief-api"}

    @app.get("/")
    async def pwa_shell() -> FileResponse:
        return FileResponse(PWA_DIR / "index.html")

    @app.post("/api/debrief/sessions", response_model=SessionCreateResponse)
    async def create_debrief_session(req: SessionCreateRequest) -> SessionCreateResponse:
        sid = create_session(DB_PATH, req.session_id)
        return SessionCreateResponse(session_id=sid, status="created")

    @app.post("/api/debrief/sessions/{session_id}/start", response_model=SessionStatusResponse)
    async def start_debrief_session(session_id: str) -> SessionStatusResponse:
        try:
            set_session_started(DB_PATH, session_id)
            session = get_session(DB_PATH, session_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="session not found")
        return SessionStatusResponse(
            session_id=str(session["session_id"]),
            status=str(session["status"]),
            started_at=session["started_at"],
            ended_at=session["ended_at"],
        )

    @app.post("/api/debrief/sessions/{session_id}/end", response_model=SessionStatusResponse)
    async def end_debrief_session(session_id: str) -> SessionStatusResponse:
        try:
            set_session_ended(DB_PATH, session_id)
            session = get_session(DB_PATH, session_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="session not found")
        return SessionStatusResponse(
            session_id=str(session["session_id"]),
            status=str(session["status"]),
            started_at=session["started_at"],
            ended_at=session["ended_at"],
        )

    return app


app = create_app()
