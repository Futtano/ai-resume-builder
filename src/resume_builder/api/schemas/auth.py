"""Pydantic schemas for authentication requests and responses."""

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Registration request body."""

    username: str = Field(
        min_length=3,
        max_length=64,
        description="Unique username (case-insensitive)",
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Password, minimum 8 characters",
    )


class UserResponse(BaseModel):
    """Public user data (never includes password hash)."""

    id: str
    username: str
    created_at: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Returned on login, register, and refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Login form fields (OAuth2 password flow compatible)."""

    username: str
    password: str


class RefreshRequest(BaseModel):
    """Refresh token request body."""

    refresh_token: str
