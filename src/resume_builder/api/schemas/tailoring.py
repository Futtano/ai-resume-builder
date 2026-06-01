"""Request and response schemas for tailoring and export endpoints."""

from pydantic import BaseModel


class TailorResponse(BaseModel):
    """Returned when tailoring is enqueued (202)."""

    task_id: str
    status: str = "queued"
    job_count: int


class TailorStatusResponse(BaseModel):
    """Returned when polling tailoring progress."""

    status: str  # "running" | "completed" | "failed"
    total_jobs: int = 0
    completed_jobs: int = 0
    errors: list[str] = []


class ExportItem(BaseModel):
    """A single exportable .docx file."""

    filename: str
    size: int
    job_title: str
    company: str
    confidence_score: int


class ExportListResponse(BaseModel):
    """Returned when listing exports for a session."""

    exports: list[ExportItem]
