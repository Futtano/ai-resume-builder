"""Request and response schemas for job endpoints."""

from pydantic import BaseModel, Field

from resume_builder.models import JobRequirements


class QueueJobRequest(BaseModel):
    """Body for POST /sessions/{id}/jobs."""

    url: str | None = Field(None, description="URL to a job posting")
    text: str | None = Field(None, description="Raw job description text")


class JobListResponse(BaseModel):
    """Returned when listing queued jobs."""

    jobs: list[JobRequirements]
