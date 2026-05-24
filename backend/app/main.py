from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .db import (
    create_session,
    get_latest_transcript,
    get_session,
    get_session_transcripts,
    init_sqlite,
    save_transcript,
    set_session_ended,
    set_session_started,
)
from .llm_debrief_openai import OpenAIDebriefError, generate_debrief_document_openai
from .llm_openai import OpenAIFollowupError, generate_followup_question_openai
from .models import (
    AudioUploadResponse,
    DebriefDocumentResponse,
    FollowUpAudioResponse,
    FollowUpQuestionResponse,
    SessionCreateResponse,
    SessionStatusResponse,
)
from .stt_openai import OpenAITranscriptionError, transcribe_file_openai
from .tts_kokoro import KokoroTTSError, synthesize_kokoro_tts

ROOT = Path(__file__).resolve().parents[2]
PWA_DIR = ROOT / "frontend" / "pwa"
DB_PATH = ROOT / "data" / "voice_debrief.sqlite3"
UPLOADS_DIR = ROOT / "data" / "uploads"
AUDIO_DIR = ROOT / "data" / "audio"
GENERATED_DOCS_DIR = ROOT / "data" / "generated_docs"


class SessionCreateRequest(BaseModel):
    session_id: str | None = None


def create_app() -> FastAPI:
    app = FastAPI(title="Voice Debrief Assistant API")
    init_sqlite(DB_PATH)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_DOCS_DIR.mkdir(parents=True, exist_ok=True)

    app.mount("/pwa", StaticFiles(directory=str(PWA_DIR)), name="pwa")
    app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")

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

    @app.post("/api/debrief/audio-upload", response_model=AudioUploadResponse)
    async def upload_debrief_audio(file: UploadFile = File(...)) -> AudioUploadResponse:
        upload_id = uuid4().hex[:16]
        suffix = Path(file.filename or "audio.webm").suffix or ".webm"
        target = UPLOADS_DIR / f"{upload_id}{suffix}"
        payload = await file.read()
        target.write_bytes(payload)
        return AudioUploadResponse(
            upload_id=upload_id,
            filename=target.name,
            bytes_received=len(payload),
        )

    @app.post("/api/debrief/sessions/{session_id}/transcribe")
    async def transcribe_session_audio(session_id: str, file: UploadFile = File(...)) -> dict:
        try:
            _ = get_session(DB_PATH, session_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="session not found")

        upload_id = uuid4().hex[:16]
        suffix = Path(file.filename or "audio.webm").suffix or ".webm"
        target = UPLOADS_DIR / f"{session_id}-{upload_id}{suffix}"
        payload = await file.read()
        target.write_bytes(payload)

        try:
            result = transcribe_file_openai(target)
        except OpenAITranscriptionError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        save_transcript(DB_PATH, session_id, result["text"], result.get("model"))
        return {
            "session_id": session_id,
            "transcript_text": result["text"],
            "stt_model": result.get("model"),
            "bytes_received": len(payload),
        }

    @app.post("/api/debrief/sessions/{session_id}/follow-up-question", response_model=FollowUpQuestionResponse)
    async def generate_followup_question(session_id: str) -> FollowUpQuestionResponse:
        try:
            _ = get_session(DB_PATH, session_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="session not found")

        latest = get_latest_transcript(DB_PATH, session_id)
        if not latest or not str(latest.get("transcript_text") or "").strip():
            raise HTTPException(status_code=400, detail="No transcript available for this session")

        try:
            result = generate_followup_question_openai(transcript_text=str(latest["transcript_text"]))
        except OpenAIFollowupError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        return FollowUpQuestionResponse(
            session_id=session_id,
            follow_up_question=result["question"],
            llm_model=result["model"],
        )

    @app.post("/api/debrief/sessions/{session_id}/follow-up-audio", response_model=FollowUpAudioResponse)
    async def generate_followup_audio(session_id: str) -> FollowUpAudioResponse:
        try:
            _ = get_session(DB_PATH, session_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="session not found")

        latest = get_latest_transcript(DB_PATH, session_id)
        if not latest or not str(latest.get("transcript_text") or "").strip():
            raise HTTPException(status_code=400, detail="No transcript available for this session")

        try:
            llm_result = generate_followup_question_openai(transcript_text=str(latest["transcript_text"]))
            audio_path = synthesize_kokoro_tts(text=llm_result["question"])
        except OpenAIFollowupError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except KokoroTTSError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        return FollowUpAudioResponse(
            session_id=session_id,
            follow_up_question=llm_result["question"],
            llm_model=llm_result["model"],
            tts_provider="kokoro",
            audio_url=f"/audio/{audio_path.name}",
        )

    @app.post("/api/debrief/sessions/{session_id}/generate-document", response_model=DebriefDocumentResponse)
    async def generate_debrief_document(session_id: str) -> DebriefDocumentResponse:
        try:
            _ = get_session(DB_PATH, session_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="session not found")

        transcripts = get_session_transcripts(DB_PATH, session_id)
        if not transcripts:
            raise HTTPException(status_code=400, detail="No transcript available for this session")

        transcript_bundle = "\n\n".join(
            f"[{idx+1}] {t['transcript_text']}" for idx, t in enumerate(transcripts) if str(t.get("transcript_text") or "").strip()
        ).strip()
        if not transcript_bundle:
            raise HTTPException(status_code=400, detail="No transcript available for this session")

        try:
            result = generate_debrief_document_openai(transcript_text=transcript_bundle)
        except OpenAIDebriefError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        doc_path = GENERATED_DOCS_DIR / f"{session_id}-{result['slug']}.md"
        doc_path.write_text(result["markdown"], encoding="utf-8")

        return DebriefDocumentResponse(
            session_id=session_id,
            title=result["title"],
            llm_model=result["model"],
            file_path=str(doc_path),
            markdown=result["markdown"],
        )

    @app.get("/api/debrief/sessions/{session_id}/document-download")
    async def download_debrief_document(session_id: str) -> FileResponse:
        try:
            _ = get_session(DB_PATH, session_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="session not found")

        candidates = sorted(
            GENERATED_DOCS_DIR.glob(f"{session_id}-*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            raise HTTPException(status_code=404, detail="no generated document for this session")

        target = candidates[0]
        return FileResponse(path=target, media_type="text/markdown", filename=target.name)

    return app


app = create_app()
