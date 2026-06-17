"""FastAPI dependencies — stores, services.

Wire everything via Depends() so route handlers stay thin.
"""

from fastapi import Depends

from resume_builder.api.stores.base import SessionStore
from resume_builder.api.stores.file_store import FileSessionStore

DEFAULT_USER_ID = "default"


def get_default_user_id() -> str:
    """Return the default user ID (auth removed — will be rebuilt later)."""
    return DEFAULT_USER_ID


# ── Stores ──


def get_session_store() -> SessionStore:
    """Return the session store singleton (file-based for MVP)."""
    return FileSessionStore()


# ── Services (lazy import to avoid circular deps) ──


def get_session_service(
    store: SessionStore = Depends(get_session_store),
):
    """Return InteractiveSessionService wired with the session store."""
    from resume_builder.api.services.session_service import InteractiveSessionService

    return InteractiveSessionService(store)
