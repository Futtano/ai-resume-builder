"""V1 API router — assembles all endpoint routers under /api/v1.

Auth (X-API-Key) is applied once at this level — every endpoint
under /api/v1 requires a valid key.
"""

from fastapi import APIRouter, Depends

from resume_builder.api.deps import get_current_user, get_session_service
from resume_builder.api.schemas.common import TaskStatusResponse
from resume_builder.api.v1.endpoints import (
    conversation,
    jobs,
    resume,
    sessions,
    tailoring,
)

api_router = APIRouter(dependencies=[Depends(get_current_user)])

# ── Sub-routers ──
api_router.include_router(sessions.router, prefix="/sessions")
api_router.include_router(resume.router, prefix="/sessions")
api_router.include_router(jobs.router, prefix="/sessions")
api_router.include_router(tailoring.router, prefix="/sessions")
api_router.include_router(conversation.router, prefix="/sessions")

# ── Cross-cutting: task status (no session context required) ──


@api_router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    service=Depends(get_session_service),
) -> TaskStatusResponse:
    """Poll the status of an async task (parse, tailor, etc.)."""
    task = service.get_task_status(task_id)
    if task is None:
        return TaskStatusResponse(status="not_found")
    return TaskStatusResponse(
        status=task["status"],
        result=task.get("result"),
        error=task.get("error"),
    )
