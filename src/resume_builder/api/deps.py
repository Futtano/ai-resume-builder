"""FastAPI dependencies — auth, stores, services.

Wire everything via Depends() so route handlers stay thin.
"""

from fastapi import Depends, Header, HTTPException

from resume_builder.api.core.config import ApiSettings, get_api_settings
from resume_builder.api.stores.base import SessionStore
from resume_builder.api.stores.file_store import FileSessionStore

# ── Auth ──


async def get_current_user(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    settings: ApiSettings = Depends(get_api_settings),
) -> str:
    """Validate the X-API-Key header and return the corresponding user ID.

    Raises 401 if the key is missing or unknown.
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    user_id = settings.api_keys.get(x_api_key)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user_id


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
