"""Resume upload, parse, and edit endpoints."""

from fastapi import APIRouter, Depends, UploadFile

from resume_builder.api.deps import get_current_user, get_session_service
from resume_builder.api.schemas.common import TaskResponse
from resume_builder.api.schemas.resume import (
    EditResumeRequest,
    EditResumeResponse,
    ResumeResponse,
    ResumeUploadResponse,
)
from resume_builder.api.services.session_service import InteractiveSessionService

router = APIRouter(tags=["resume"])


@router.post("/{session_id}/resume", response_model=ResumeUploadResponse)
async def upload_resume(
    session_id: str,
    file: UploadFile,
    user_id: str = Depends(get_current_user),
    service: InteractiveSessionService = Depends(get_session_service),
) -> ResumeUploadResponse:
    """Upload a resume PDF for the session."""
    content = await file.read()
    await service.upload_resume(
        user_id, session_id, content, file.filename or "resume.pdf"
    )
    return ResumeUploadResponse(
        filename=file.filename or "resume.pdf",
        size=len(content),
    )


@router.post(
    "/{session_id}/resume/parse",
    response_model=TaskResponse,
    status_code=202,
)
async def parse_resume(
    session_id: str,
    user_id: str = Depends(get_current_user),
    service: InteractiveSessionService = Depends(get_session_service),
) -> TaskResponse:
    """Trigger AI parsing of the uploaded resume. Returns a task_id for polling."""
    task_id = await service.parse_resume(user_id, session_id)
    return TaskResponse(task_id=task_id)


@router.get("/{session_id}/resume", response_model=ResumeResponse)
async def get_resume(
    session_id: str,
    user_id: str = Depends(get_current_user),
    service: InteractiveSessionService = Depends(get_session_service),
) -> ResumeResponse:
    """Get the current working resume (ParsedResume)."""
    state = await service.get_session(user_id, session_id)
    return ResumeResponse(working_resume=state.working_resume)


@router.patch("/{session_id}/resume", response_model=EditResumeResponse)
async def edit_resume(
    session_id: str,
    body: EditResumeRequest,
    user_id: str = Depends(get_current_user),
    service: InteractiveSessionService = Depends(get_session_service),
) -> EditResumeResponse:
    """Apply a natural-language edit to the working resume.

    This is the core interactive pattern. The instruction is sent to the LLM
    along with the current resume. The LLM returns a JSON patch that is
    merged into the working resume.
    """
    result = await service.apply_edit(user_id, session_id, body.instruction)
    return EditResumeResponse(**result)
