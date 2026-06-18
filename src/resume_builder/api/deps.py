"""FastAPI dependencies — auth, stores, services.

Wire everything via Depends() so route handlers stay thin.
"""

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from resume_builder.api.auth.tokens import decode_access_token
from resume_builder.api.stores.base import SessionStore
from resume_builder.api.stores.sql_store import SQLSessionStore

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user_id(
    token: str = Depends(oauth2_scheme),
) -> str:
    """Extract and validate the JWT access token. Returns the user_id.

    Replaces the old get_default_user_id() — same return type (str),
    so no endpoint code needs to change.
    """
    try:
        payload = decode_access_token(token)
    except JWTError as err:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from err

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return user_id


# ── Stores ──


def get_session_store() -> SessionStore:
    """Return the session store (SQLite-backed)."""
    return SQLSessionStore()


# ── Services (lazy import to avoid circular deps) ──


def get_session_service(
    store: SessionStore = Depends(get_session_store),
):
    """Return InteractiveSessionService wired with the session store."""
    from resume_builder.api.services.session_service import InteractiveSessionService

    return InteractiveSessionService(store)
