import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .db import (
    create_session,
    get_latest_transcript,
    get_session,
    get_session_memory_facts,
    get_session_skill_hints,
    get_session_transcripts,
    get_usage_totals,
    init_sqlite,
    log_usage_event,
    save_memory_facts,
    save_skill_hints,
    save_transcript,
    set_session_ended,
    set_session_started,
)
from .hermes_memory import extract_memory_facts_from_transcript
from .hermes_skills import extract_skill_hints_from_transcript
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


class FeedbackEntryRequest(BaseModel):
    user_id: str
    trust_score: int
    cognitive_load_score: int
    notes: str = ''
    next_changes: str = ''


def _request_user_id(x_user_id: str | None) -> str:
    return (x_user_id or 'local-bob').strip() or 'local-bob'


def _assert_owner(session: dict[str, str | None], user_id: str) -> None:
    owner = str(session.get('owner_user_id') or 'local-bob')
    if owner != user_id:
        raise HTTPException(status_code=403, detail='Not your session')


def _assert_admin(x_admin_key: str | None) -> None:
    expected = os.getenv('ADMIN_API_KEY', 'dev-admin-key')
    if (x_admin_key or '').strip() != expected:
        raise HTTPException(status_code=401, detail='Invalid admin key')


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

    @app.get('/api/admin/usage-summary')
    async def usage_summary(x_admin_key: str | None = Header(default=None)) -> dict:
        _assert_admin(x_admin_key)
        return {'totals': get_usage_totals(DB_PATH)}

    @app.post('/api/admin/feedback-entry')
    async def ingest_feedback_entry(
        req: FeedbackEntryRequest,
        x_admin_key: str | None = Header(default=None),
    ) -> dict:
        _assert_admin(x_admin_key)
        if not (1 <= req.trust_score <= 5 and 1 <= req.cognitive_load_score <= 5):
            raise HTTPException(status_code=400, detail='Scores must be 1-5')

        log_path = Path(os.getenv('FEEDBACK_LOG_PATH', str(ROOT / 'docs' / 'validation' / 'feedback_log.csv')))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if not log_path.exists():
            log_path.write_text('timestamp_utc,user_id,trust_score,cognitive_load_score,notes,next_changes\n', encoding='utf-8')

        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        with log_path.open('a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                req.user_id,
                req.trust_score,
                req.cognitive_load_score,
                req.notes,
                req.next_changes,
            ])

        log_usage_event(DB_PATH, event_type='feedback_received', user_id=req.user_id)
        return {'ok': True, 'log_path': str(log_path), 'timestamp_utc': timestamp}

    @app.get("/")
    async def pwa_shell() -> FileResponse:
        return FileResponse(PWA_DIR / "index.html")

    @app.post("/api/debrief/sessions", response_model=SessionCreateResponse)
    async def create_debrief_session(req: SessionCreateRequest, x_user_id: str | None = Header(default=None)) -> SessionCreateResponse:
        user_id = _request_user_id(x_user_id)
        sid = create_session(DB_PATH, req.session_id, owner_user_id=user_id)
        log_usage_event(DB_PATH, event_type='session_created', user_id=user_id, session_id=sid)
        return SessionCreateResponse(session_id=sid, status="created")

    @app.post("/api/debrief/sessions/{session_id}/start", response_model=SessionStatusResponse)
    async def start_debrief_session(session_id: str, x_user_id: str | None = Header(default=None)) -> SessionStatusResponse:
        user_id = _request_user_id(x_user_id)
        try:
            session = get_session(DB_PATH, session_id)
            _assert_owner(session, user_id)
            set_session_started(DB_PATH, session_id)
            session = get_session(DB_PATH, session_id)
            log_usage_event(DB_PATH, event_type='session_started', user_id=user_id, session_id=session_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="session not found")
        return SessionStatusResponse(
            session_id=str(session["session_id"]),
            status=str(session["status"]),
            started_at=session["started_at"],
            ended_at=session["ended_at"],
        )

    @app.post("/api/debrief/sessions/{session_id}/end", response_model=SessionStatusResponse)
    async def end_debrief_session(session_id: str, x_user_id: str | None = Header(default=None)) -> SessionStatusResponse:
        user_id = _request_user_id(x_user_id)
        try:
            session = get_session(DB_PATH, session_id)
            _assert_owner(session, user_id)
            set_session_ended(DB_PATH, session_id)
            session = get_session(DB_PATH, session_id)
            log_usage_event(DB_PATH, event_type='session_ended', user_id=user_id, session_id=session_id)
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
    async def transcribe_session_audio(
        session_id: str,
        file: UploadFile = File(...),
        x_user_id: str | None = Header(default=None),
    ) -> dict:
        user_id = _request_user_id(x_user_id)
        try:
            session = get_session(DB_PATH, session_id)
            _assert_owner(session, user_id)
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
        memory_facts = extract_memory_facts_from_transcript(result["text"])
        save_memory_facts(DB_PATH, session_id, memory_facts)
        skill_hints = extract_skill_hints_from_transcript(result["text"])
        save_skill_hints(DB_PATH, session_id, skill_hints)
        log_usage_event(DB_PATH, event_type='transcribe', user_id=user_id, session_id=session_id)
        return {
            "session_id": session_id,
            "transcript_text": result["text"],
            "stt_model": result.get("model"),
            "bytes_received": len(payload),
        }

    @app.post("/api/debrief/sessions/{session_id}/follow-up-question", response_model=FollowUpQuestionResponse)
    async def generate_followup_question(
        session_id: str,
        x_user_id: str | None = Header(default=None),
    ) -> FollowUpQuestionResponse:
        user_id = _request_user_id(x_user_id)
        try:
            session = get_session(DB_PATH, session_id)
            _assert_owner(session, user_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="session not found")

        latest = get_latest_transcript(DB_PATH, session_id)
        if not latest or not str(latest.get("transcript_text") or "").strip():
            raise HTTPException(status_code=400, detail="No transcript available for this session")

        try:
            result = generate_followup_question_openai(
                transcript_text=str(latest["transcript_text"]),
                memory_facts=get_session_memory_facts(DB_PATH, session_id),
                skill_hints=get_session_skill_hints(DB_PATH, session_id),
            )
            log_usage_event(DB_PATH, event_type='followup_question', user_id=user_id, session_id=session_id)
        except OpenAIFollowupError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        return FollowUpQuestionResponse(
            session_id=session_id,
            follow_up_question=result["question"],
            llm_model=result["model"],
        )

    @app.post("/api/debrief/sessions/{session_id}/follow-up-audio", response_model=FollowUpAudioResponse)
    async def generate_followup_audio(
        session_id: str,
        x_user_id: str | None = Header(default=None),
    ) -> FollowUpAudioResponse:
        user_id = _request_user_id(x_user_id)
        try:
            session = get_session(DB_PATH, session_id)
            _assert_owner(session, user_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="session not found")

        latest = get_latest_transcript(DB_PATH, session_id)
        if not latest or not str(latest.get("transcript_text") or "").strip():
            raise HTTPException(status_code=400, detail="No transcript available for this session")

        try:
            llm_result = generate_followup_question_openai(
                transcript_text=str(latest["transcript_text"]),
                memory_facts=get_session_memory_facts(DB_PATH, session_id),
                skill_hints=get_session_skill_hints(DB_PATH, session_id),
            )
            audio_path = synthesize_kokoro_tts(text=llm_result["question"])
            log_usage_event(DB_PATH, event_type='followup_audio', user_id=user_id, session_id=session_id)
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
    async def generate_debrief_document(
        session_id: str,
        x_user_id: str | None = Header(default=None),
    ) -> DebriefDocumentResponse:
        user_id = _request_user_id(x_user_id)
        try:
            session = get_session(DB_PATH, session_id)
            _assert_owner(session, user_id)
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

        user_docs_dir = GENERATED_DOCS_DIR / user_id
        user_docs_dir.mkdir(parents=True, exist_ok=True)
        doc_path = user_docs_dir / f"{session_id}-{result['slug']}.md"
        doc_path.write_text(result["markdown"], encoding="utf-8")
        log_usage_event(DB_PATH, event_type='document_generated', user_id=user_id, session_id=session_id)

        return DebriefDocumentResponse(
            session_id=session_id,
            title=result["title"],
            llm_model=result["model"],
            file_path=str(doc_path),
            markdown=result["markdown"],
        )

    @app.get("/api/debrief/sessions/{session_id}/document-download")
    async def download_debrief_document(
        session_id: str,
        x_user_id: str | None = Header(default=None),
    ) -> FileResponse:
        user_id = _request_user_id(x_user_id)
        try:
            session = get_session(DB_PATH, session_id)
            _assert_owner(session, user_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="session not found")

        user_docs_dir = GENERATED_DOCS_DIR / user_id
        candidates = sorted(
            user_docs_dir.glob(f"{session_id}-*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            raise HTTPException(status_code=404, detail="no generated document for this session")

        target = candidates[0]
        log_usage_event(DB_PATH, event_type='document_downloaded', user_id=user_id, session_id=session_id)
        return FileResponse(path=target, media_type="text/markdown", filename=target.name)

    return app


app = create_app()
