"""Tailoring and export endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from resume_builder.api.deps import get_current_user_id, get_session_service
from resume_builder.api.errors import AppError
from resume_builder.api.schemas.tailoring import (
    ExportItem,
    ExportListResponse,
    TailorResponse,
    TailorStatusResponse,
)
from resume_builder.api.services.session_service import InteractiveSessionService

router = APIRouter(tags=["tailoring"])


@router.post("/{session_id}/tailor", status_code=202, response_model=TailorResponse)
async def tailor(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    service: InteractiveSessionService = Depends(get_session_service),
) -> TailorResponse:
    """Run AI tailoring against all queued jobs.

    Enqueues ResumeBuilderCrew (3-agent sequential pipeline) for every
    queued job posting. Returns a task_id for polling.
    """
    state = await service.get_session(user_id, session_id)
    job_count = len(state.parsed_job_postings)
    task_id = await service.run_tailoring(user_id, session_id)
    return TailorResponse(task_id=task_id, job_count=job_count)


@router.get("/{session_id}/tailor/status", response_model=TailorStatusResponse)
async def tailor_status(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    service: InteractiveSessionService = Depends(get_session_service),
) -> TailorStatusResponse:
    """Check the progress of a tailoring run."""
    info = await service.get_tailor_status(user_id, session_id)
    return TailorStatusResponse(
        status="completed" if info["tailored_resumes"] else "running",
        total_jobs=info["total_jobs"],
        completed_jobs=len(info["tailored_resumes"]),
    )


@router.post(
    "/{session_id}/exports", status_code=200, response_model=ExportListResponse
)
async def generate_exports(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    service: InteractiveSessionService = Depends(get_session_service),
) -> ExportListResponse:
    """Generate .docx files from all tailored resumes in this session.

    Call this after tailoring completes to render the .docx files.
    """
    exports = await service.export_resumes(user_id, session_id)
    return ExportListResponse(exports=[ExportItem(**e) for e in exports])


@router.get("/{session_id}/exports", response_model=ExportListResponse)
async def list_exports(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    service: InteractiveSessionService = Depends(get_session_service),
) -> ExportListResponse:
    """List generated .docx files for a session."""
    exports = await service.get_exports(user_id, session_id)
    return ExportListResponse(exports=[ExportItem(**e) for e in exports])


@router.get("/{session_id}/exports/{filename}")
async def download_export(
    session_id: str,
    filename: str,
    user_id: str = Depends(get_current_user_id),
    service: InteractiveSessionService = Depends(get_session_service),
) -> FileResponse:
    """Download a generated .docx file."""
    path = await service.get_export_path(user_id, session_id, filename)
    if path is None:
        raise AppError(404, "FILE_NOT_FOUND", f"File {filename} not found")
    return FileResponse(
        path=path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )
