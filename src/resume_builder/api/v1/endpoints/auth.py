"""Authentication endpoints — register, login, refresh, logout."""

import hashlib

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from resume_builder.api.auth.hashing import hash_password, verify_password
from resume_builder.api.auth.tokens import (
    create_access_token,
    create_refresh_token,
)
from resume_builder.api.core.database import get_db, utcnow
from resume_builder.api.models.refresh_token import RefreshToken
from resume_builder.api.models.user import User
from resume_builder.api.schemas.auth import (
    RefreshRequest,
    TokenResponse,
    UserCreate,
)
from resume_builder.logger import get_logger

logger = get_logger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Create a new user account and return tokens (auto-login)."""
    # Check uniqueness
    result = await db.execute(
        select(User).where(User.username == body.username.lower())
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Username already taken")

    user = User(
        username=body.username.lower(),
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.flush()

    # Build tokens
    access_token = create_access_token(user.id, user.username)
    raw, token_hash, expires_at = create_refresh_token()

    refresh = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(refresh)
    await db.commit()

    logger.info("User registered: %s (id=%s)", user.username, user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw,
    )


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with username and password (OAuth2 form-encoded). Returns tokens."""
    result = await db.execute(
        select(User).where(User.username == form.username.lower())
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    access_token = create_access_token(user.id, user.username)
    raw, token_hash, expires_at = create_refresh_token()

    refresh = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(refresh)
    await db.commit()

    logger.info("User logged in: %s", user.username)
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw,
    )


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange a valid refresh token for a new token pair (rotation)."""
    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()

    if stored is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if stored.expires_at < utcnow():
        await db.delete(stored)
        await db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # Get user for new token claims
    user_result = await db.execute(select(User).where(User.id == stored.user_id))
    user = user_result.scalar_one()

    # Rotate: delete old, create new
    await db.delete(stored)

    access_token = create_access_token(user.id, user.username)
    raw, new_hash, expires_at = create_refresh_token()

    new_refresh = RefreshToken(
        user_id=user.id,
        token_hash=new_hash,
        expires_at=expires_at,
    )
    db.add(new_refresh)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw,
    )


@auth_router.post("/logout", status_code=204)
async def logout(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke a refresh token (logout)."""
    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()

    await db.execute(delete(RefreshToken).where(RefreshToken.token_hash == token_hash))
    await db.commit()
