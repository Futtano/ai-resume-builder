"""Centralised error handling for the API."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from resume_builder.logger import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Application-level exception with HTTP semantics.

    Raised by services/endpoints when something goes wrong.
    The exception handler below converts it to a structured JSON response.
    """

    def __init__(
        self,
        status_code: int,
        error_code: str,
        detail: str,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail
        super().__init__(detail)


# ── Predefined errors for common cases ──


def session_not_found(session_id: str) -> AppError:
    return AppError(404, "SESSION_NOT_FOUND", f"Session {session_id} not found")


def task_not_found(task_id: str) -> AppError:
    return AppError(404, "TASK_NOT_FOUND", f"Task {task_id} not found or expired")


def no_resume_loaded() -> AppError:
    return AppError(
        409, "NO_RESUME_LOADED", "No resume has been parsed for this session yet"
    )


def no_jobs_queued() -> AppError:
    return AppError(409, "NO_JOBS_QUEUED", "No jobs are queued for tailoring")


def invalid_instruction(detail: str = "") -> AppError:
    return AppError(
        422,
        "INVALID_INSTRUCTION",
        detail or "The edit instruction could not be processed",
    )


def llm_failure(detail: str = "") -> AppError:
    return AppError(502, "LLM_FAILURE", detail or "The AI service returned an error")


def crew_failure(detail: str = "") -> AppError:
    return AppError(
        502,
        "CREW_FAILURE",
        detail or "The resume processing engine encountered an error",
    )


def too_many_requests() -> AppError:
    return AppError(
        503, "TOO_MANY_REQUESTS", "The server is at capacity, please try again later"
    )


# ── FastAPI exception handler ──


def register_handlers(app: FastAPI) -> None:
    """Register the AppError exception handler on the FastAPI app."""

    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("AppError %s: %s", exc.error_code, exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error_code": exc.error_code,
            },
        )
