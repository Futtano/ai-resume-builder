"""Session CRUD endpoints."""

from fastapi import APIRouter, Depends, Query

from resume_builder.api.deps import get_current_user, get_session_service
from resume_builder.api.schemas.sessions import (
    SessionListResponse,
    SessionResponse,
)
from resume_builder.api.services.session_service import InteractiveSessionService

router = APIRouter(tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    user_id: str = Depends(get_current_user),
    service: InteractiveSessionService = Depends(get_session_service),
) -> SessionResponse:
    """Create a new interactive resume tailoring session."""
    state = await service.create_session(user_id)
    return SessionResponse(session_id=state.session_id, state=state)


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user),
    service: InteractiveSessionService = Depends(get_session_service),
) -> SessionListResponse:
    """List sessions for the authenticated user, newest first."""
    items, total = await service.list_sessions(user_id, limit, offset)
    return SessionListResponse(
        items=[item.__dict__ if hasattr(item, "__dict__") else item for item in items],
        total=total,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user),
    service: InteractiveSessionService = Depends(get_session_service),
) -> SessionResponse:
    """Get full state for a session."""
    state = await service.get_session(user_id, session_id)
    return SessionResponse(session_id=state.session_id, state=state)


@router.delete("/{session_id}", status_code=200)
async def delete_session(
    session_id: str,
    user_id: str = Depends(get_current_user),
    service: InteractiveSessionService = Depends(get_session_service),
) -> dict[str, bool]:
    """Delete a session and all its files."""
    deleted = await service.delete_session(user_id, session_id)
    return {"deleted": deleted}
