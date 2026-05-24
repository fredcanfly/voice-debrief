from pydantic import BaseModel


class SessionCreateResponse(BaseModel):
    session_id: str
    status: str


class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    started_at: str | None = None
    ended_at: str | None = None
