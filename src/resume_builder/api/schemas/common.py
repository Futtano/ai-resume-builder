"""Shared API schemas — error responses, task status, pagination."""

from pydantic import BaseModel


class APIError(BaseModel):
    """Standard error response body."""

    detail: str
    error_code: str


class TaskResponse(BaseModel):
    """Returned when a long-running operation is enqueued (202)."""

    task_id: str
    status: str = "queued"


class TaskStatusResponse(BaseModel):
    """Returned when polling a task's progress."""

    status: str  # "queued" | "running" | "completed" | "failed"
    result: object | None = None
    error: APIError | None = None
