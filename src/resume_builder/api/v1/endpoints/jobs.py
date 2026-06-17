"""Job queue endpoints."""

from fastapi import APIRouter, Depends

from resume_builder.api.deps import get_default_user_id, get_session_service
from resume_builder.api.errors import AppError
from resume_builder.api.schemas.common import TaskResponse
from resume_builder.api.schemas.jobs import JobListResponse, QueueJobRequest
from resume_builder.api.services.session_service import InteractiveSessionService

router = APIRouter(tags=["jobs"])


@router.post("/{session_id}/jobs", status_code=202)
async def queue_job(
    session_id: str,
    body: QueueJobRequest,
    user_id: str = Depends(get_default_user_id),
    service: InteractiveSessionService = Depends(get_session_service),
) -> TaskResponse:
    """Queue a job posting for later tailoring.

    Accepts a URL or raw text as a JSON body.
    """
    if body.url or body.text:
        task_id = await service.queue_job(user_id, session_id, body.url, body.text)
    else:
        raise AppError(400, "MISSING_SOURCE", "Provide a URL, text, or file upload")

    return TaskResponse(task_id=task_id)


@router.get("/{session_id}/jobs", response_model=JobListResponse)
async def list_jobs(
    session_id: str,
    user_id: str = Depends(get_default_user_id),
    service: InteractiveSessionService = Depends(get_session_service),
) -> JobListResponse:
    """List queued job postings for a session."""
    jobs = await service.list_jobs(user_id, session_id)
    return JobListResponse(jobs=jobs)


@router.delete("/{session_id}/jobs/{job_index}", status_code=200)
async def remove_job(
    session_id: str,
    job_index: int,
    user_id: str = Depends(get_default_user_id),
    service: InteractiveSessionService = Depends(get_session_service),
) -> dict[str, bool]:
    """Remove a queued job by its list index."""
    await service.remove_job(user_id, session_id, job_index)
    return {"deleted": True}
