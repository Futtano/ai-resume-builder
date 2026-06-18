"""JWT access token and opaque refresh token utilities."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from jose import jwt

from resume_builder.api.core.config import get_api_settings

settings = get_api_settings()


def _get_secret_key() -> str:
    key = settings.api_secret_key
    if not key:
        raise RuntimeError(
            "API_SECRET_KEY is not set. Generate one and add it to your .env file."
        )
    return key


def create_access_token(user_id: str, username: str) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.api_access_token_expire_minutes
    )
    payload = {
        "sub": user_id,
        "username": username,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }
    return jwt.encode(payload, _get_secret_key(), algorithm="HS256")


def create_refresh_token() -> tuple[str, str, datetime]:
    """Create an opaque refresh token.

    Returns (raw_token, sha256_hash, expires_at).
    The raw token is sent to the client; the hash is stored in the DB.
    """
    raw = secrets.token_hex(32)  # 64 hex chars
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(
        days=settings.api_refresh_token_expire_days
    )
    return raw, token_hash, expires_at


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token. Raises JWTError on failure."""
    return jwt.decode(token, _get_secret_key(), algorithms=["HS256"])
