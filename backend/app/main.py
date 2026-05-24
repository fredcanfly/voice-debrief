from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import init_sqlite

ROOT = Path(__file__).resolve().parents[2]
PWA_DIR = ROOT / "frontend" / "pwa"
DB_PATH = ROOT / "data" / "voice_debrief.sqlite3"


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

    return app


app = create_app()
