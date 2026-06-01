"""Request and response schemas for session endpoints."""

from pydantic import BaseModel

from resume_builder.models import InteractiveResumeState


class SessionResponse(BaseModel):
    """Returned after creating or fetching a session."""

    session_id: str
    state: InteractiveResumeState


class SessionSummary(BaseModel):
    """Lightweight summary for listing sessions."""

    session_id: str
    candidate_name: str
    skills_count: int
    experience_count: int
    job_count: int
    tailored_count: int
    last_updated: str  # ISO 8601


class SessionListResponse(BaseModel):
    """Paginated session list."""

    items: list[SessionSummary]
    total: int
