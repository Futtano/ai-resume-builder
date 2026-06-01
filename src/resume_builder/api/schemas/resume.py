"""Request and response schemas for resume endpoints."""

from pydantic import BaseModel, Field

from resume_builder.models import ConversationEntry, ParsedResume


class ResumeUploadResponse(BaseModel):
    """Returned after uploading a resume PDF."""

    filename: str
    size: int


class EditResumeRequest(BaseModel):
    """Body for PATCH /sessions/{id}/resume — natural language edit."""

    instruction: str = Field(
        ...,
        min_length=1,
        description="Natural language instruction describing what to change",
    )


class EditResumeResponse(BaseModel):
    """Returned after a successful edit."""

    updated_fields: list[str]
    working_resume: ParsedResume
    conversation_entry: ConversationEntry


class ResumeResponse(BaseModel):
    """Returned when fetching the current working resume."""

    working_resume: ParsedResume | None
