from pydantic import BaseModel


class SessionCreateResponse(BaseModel):
    session_id: str
    status: str


class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    started_at: str | None = None
    ended_at: str | None = None


class AudioUploadResponse(BaseModel):
    upload_id: str
    filename: str
    bytes_received: int


class FollowUpQuestionResponse(BaseModel):
    session_id: str
    follow_up_question: str
    llm_model: str
