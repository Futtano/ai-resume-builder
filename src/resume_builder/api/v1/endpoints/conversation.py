"""Conversation history endpoint."""

from fastapi import APIRouter, Depends

from resume_builder.api.deps import get_current_user, get_session_service
from resume_builder.api.services.session_service import InteractiveSessionService
from resume_builder.models import ConversationEntry

router = APIRouter(tags=["conversation"])


@router.get("/{session_id}/conversation")
async def get_conversation(
    session_id: str,
    user_id: str = Depends(get_current_user),
    service: InteractiveSessionService = Depends(get_session_service),
) -> dict[str, list[ConversationEntry]]:
    """Get the full conversation history for a session."""
    entries = await service.get_conversation(user_id, session_id)
    return {"entries": entries}
