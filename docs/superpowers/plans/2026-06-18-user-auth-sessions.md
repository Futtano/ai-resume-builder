# User Authentication & Session Scoping — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add username/password authentication with JWT tokens and migrate session persistence from file-based JSON to SQLite, scoping all sessions to real user IDs.

**Architecture:** SQLAlchemy async models for User, Session (SQLSessionStore replacing FileSessionStore), and RefreshToken. JWT access tokens (15min, HS256) + opaque refresh tokens (7-day, rotated). A FastAPI dependency replaces the hardcoded `get_default_user_id()` with JWT-bearing `get_current_user_id()` — zero changes needed in endpoint code.

**Tech Stack:** SQLAlchemy[asyncio] + aiosqlite, passlib[bcrypt], python-jose (JWT), FastAPI OAuth2PasswordBearer

## Global Constraints

- Python >=3.11,<3.14
- All async I/O via SQLAlchemy asyncio + aiosqlite
- Database file at `data/resume_builder.db` (configurable via `ApiSettings`)
- Access token: JWT HS256, 15-minute expiry
- Refresh token: opaque 64-char hex, SHA-256 hashed in DB, 7-day expiry, rotated on each use
- Passwords: bcrypt via passlib, minimum 8 characters
- Usernames: 3–64 chars, case-insensitive, unique
- `SECRET_KEY` must be set in `.env` — fail fast if missing
- All existing tests must continue to pass
- CLI code (`interactive_flow.py`, `main.py`) is NOT modified
- Endpoint files (`sessions.py`, `resume.py`, `jobs.py`, `tailoring.py`, `conversation.py`) are NOT modified

---

### Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml`

**Produces:** Four new packages available in the project environment.

- [ ] **Step 1: Add SQLAlchemy with async support**

```bash
uv add "sqlalchemy[asyncio]>=2.0.0"
```

- [ ] **Step 2: Add aiosqlite**

```bash
uv add aiosqlite
```

- [ ] **Step 3: Add passlib with bcrypt**

```bash
uv add "passlib[bcrypt]"
```

- [ ] **Step 4: Add python-jose for JWT**

```bash
uv add python-jose
```

- [ ] **Step 5: Verify install**

```bash
uv run python -c "import sqlalchemy; import aiosqlite; import passlib; import jose; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: add SQLAlchemy, aiosqlite, passlib, python-jose for auth"
```

---

### Task 2: Add Auth Settings to ApiSettings

**Files:**
- Modify: `src/resume_builder/api/core/config.py`

**Produces:** `ApiSettings` gains `api_secret_key`, `api_db_path`, and token expiry fields.

- [ ] **Step 1: Add new fields to ApiSettings**

Add these fields inside the `ApiSettings` class, after `api_task_result_ttl_seconds`:

```python
    api_secret_key: str = ""
    """Secret key for signing JWT tokens. Set via API_SECRET_KEY env var or .env."""

    api_db_path: str = "data/resume_builder.db"
    """Path to the SQLite database file."""

    api_access_token_expire_minutes: int = 15
    """JWT access token lifetime in minutes."""

    api_refresh_token_expire_days: int = 7
    """Refresh token lifetime in days."""
```

- [ ] **Step 2: Verify settings load**

```bash
uv run python -c "from resume_builder.api.core.config import get_api_settings; s = get_api_settings(); print(s.api_secret_key, s.api_db_path, s.api_access_token_expire_minutes)"
```

Expected: prints ` data/resume_builder.db 15` (empty string for secret_key since not set).

- [ ] **Step 3: Commit**

```bash
git add src/resume_builder/api/core/config.py
git commit -m "feat: add auth settings (SECRET_KEY, DB_PATH, token expiry) to ApiSettings"
```

---

### Task 3: Create Database Module

**Files:**
- Create: `src/resume_builder/api/core/database.py`

**Interfaces:**
- Produces: `engine` (AsyncEngine), `AsyncSessionLocal` (async_sessionmaker), `get_db()` (async generator yielding AsyncSession), `init_db()` (create tables), `Base` (DeclarativeBase)

- [ ] **Step 1: Write database.py**

```python
"""Async SQLAlchemy engine, session factory, and table creation."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from resume_builder.api.core.config import get_api_settings
from resume_builder.logger import get_logger

logger = get_logger(__name__)

settings = get_api_settings()
DATABASE_URL = f"sqlite+aiosqlite:///{settings.api_db_path}"

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_db():
    """FastAPI dependency: yield an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables. Called during app startup lifespan."""
    import resume_builder.api.models.user  # noqa: F401 — register ORM models
    import resume_builder.api.models.session  # noqa: F401
    import resume_builder.api.models.refresh_token  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created (if not exist)")
```

- [ ] **Step 2: Verify module imports**

```bash
uv run python -c "from resume_builder.api.core.database import engine, AsyncSessionLocal, get_db, init_db, Base; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 3: Commit**

```bash
git add src/resume_builder/api/core/database.py
git commit -m "feat: add async SQLAlchemy engine, session factory, and init_db"
```

---

### Task 4: Create SQLAlchemy Models

**Files:**
- Create: `src/resume_builder/api/models/__init__.py`
- Create: `src/resume_builder/api/models/user.py`
- Create: `src/resume_builder/api/models/session.py`
- Create: `src/resume_builder/api/models/refresh_token.py`

**Interfaces:**
- Consumes: `Base` from `api.core.database`
- Produces: `User`, `Session`, `RefreshToken` ORM models

- [ ] **Step 1: Write models/__init__.py**

```python
"""SQLAlchemy ORM models package."""
```

- [ ] **Step 2: Write models/user.py**

```python
"""User ORM model."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from resume_builder.api.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default_factory=lambda: str(uuid.uuid4())
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default_factory=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
```

- [ ] **Step 3: Write models/session.py**

```python
"""Session ORM model — persisted InteractiveResumeState."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from resume_builder.api.core.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(8), primary_key=True, default_factory=lambda: uuid.uuid4().hex[:8]
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    state_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default_factory=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
```

- [ ] **Step 4: Write models/refresh_token.py**

```python
"""RefreshToken ORM model."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from resume_builder.api.core.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default_factory=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default_factory=lambda: datetime.now(UTC)
    )
```

- [ ] **Step 5: Verify models create tables**

```bash
uv run python -c "
import asyncio
from resume_builder.api.core.database import engine, Base, init_db
asyncio.run(init_db())
print('Tables created OK')
"
```

Expected: prints `Tables created OK` (creates `data/resume_builder.db`). Delete the test DB afterward: `rm -f data/resume_builder.db`.

- [ ] **Step 6: Commit**

```bash
git add src/resume_builder/api/models/
git commit -m "feat: add User, Session, RefreshToken SQLAlchemy models"
```

---

### Task 5: Create Auth Utilities

**Files:**
- Create: `src/resume_builder/api/auth/__init__.py`
- Create: `src/resume_builder/api/auth/hashing.py`
- Create: `src/resume_builder/api/auth/tokens.py`

**Interfaces:**
- Consumes: `ApiSettings` (for SECRET_KEY, token expiry), `User` ORM model
- Produces: `hash_password(password: str) -> str`, `verify_password(plain: str, hashed: str) -> bool`, `create_access_token(user_id: str, username: str) -> str`, `create_refresh_token() -> tuple[str, str, datetime]` (raw, hash, expires_at), `decode_access_token(token: str) -> dict`

- [ ] **Step 1: Write auth/__init__.py**

```python
"""Authentication utilities — hashing and JWT tokens."""
```

- [ ] **Step 2: Write auth/hashing.py**

```python
"""Password hashing with bcrypt via passlib."""

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return bcrypt hash of the password."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)
```

- [ ] **Step 3: Write auth/tokens.py**

```python
"""JWT access token and opaque refresh token utilities."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

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
    expire = datetime.now(UTC) + timedelta(minutes=settings.api_access_token_expire_minutes)
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
    expires_at = datetime.now(UTC) + timedelta(days=settings.api_refresh_token_expire_days)
    return raw, token_hash, expires_at


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token. Raises JWTError on failure."""
    return jwt.decode(token, _get_secret_key(), algorithms=["HS256"])
```

- [ ] **Step 4: Write a quick smoke test**

```bash
uv run python -c "
from resume_builder.api.auth.hashing import hash_password, verify_password
h = hash_password('test1234')
assert verify_password('test1234', h)
assert not verify_password('wrong', h)
print('Hashing OK')
"
```

- [ ] **Step 5: Test tokens (requires SECRET_KEY in env)**

```bash
API_SECRET_KEY=test-secret-key uv run python -c "
from resume_builder.api.auth.tokens import create_access_token, create_refresh_token, decode_access_token
token = create_access_token('user-1', 'alice')
claims = decode_access_token(token)
assert claims['sub'] == 'user-1'
assert claims['username'] == 'alice'
assert claims['type'] == 'access'
raw, hash_val, expires = create_refresh_token()
assert len(raw) == 64
assert len(hash_val) == 64
print('Tokens OK')
"
```

Expected: prints `Tokens OK`.

- [ ] **Step 6: Commit**

```bash
git add src/resume_builder/api/auth/
git commit -m "feat: add password hashing and JWT token utilities"
```

---

### Task 6: Create Auth Schemas

**Files:**
- Create: `src/resume_builder/api/schemas/auth.py`

**Interfaces:**
- Produces: `UserCreate`, `UserResponse`, `TokenResponse`, `LoginRequest` Pydantic models

- [ ] **Step 1: Write schemas/auth.py**

```python
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
```

- [ ] **Step 2: Verify imports**

```bash
uv run python -c "from resume_builder.api.schemas.auth import UserCreate, UserResponse, TokenResponse; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 3: Commit**

```bash
git add src/resume_builder/api/schemas/auth.py
git commit -m "feat: add auth Pydantic schemas (UserCreate, TokenResponse, etc.)"
```

---

### Task 7: Create Auth Endpoints

**Files:**
- Create: `src/resume_builder/api/v1/endpoints/auth.py`

**Interfaces:**
- Consumes: `get_db`, `User` model, `RefreshToken` model, auth utilities, auth schemas
- Produces: `auth_router` (APIRouter with `/register`, `/login`, `/refresh`, `/logout`)

- [ ] **Step 1: Write endpoints/auth.py**

```python
"""Authentication endpoints — register, login, refresh, logout."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from resume_builder.api.auth.hashing import hash_password, verify_password
from resume_builder.api.auth.tokens import (
    create_access_token,
    create_refresh_token,
)
from resume_builder.api.core.database import get_db
from resume_builder.api.models.refresh_token import RefreshToken
from resume_builder.api.models.user import User
from resume_builder.api.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from resume_builder.logger import get_logger

logger = get_logger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["auth"])


def _make_token_response(db_user: User) -> TokenResponse:
    """Build a TokenResponse for a user. Does NOT persist the refresh token."""
    access_token = create_access_token(db_user.id, db_user.username)
    raw, token_hash, expires_at = create_refresh_token()
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw,
    ), token_hash, expires_at


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
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with username and password. Returns tokens."""
    result = await db.execute(
        select(User).where(User.username == body.username.lower())
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
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
    import hashlib

    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()

    if stored is None:
        # Token not found — possible theft. Revoke all for safety.
        # We don't know the user, so just reject.
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if stored.expires_at < datetime.now(UTC):
        await db.delete(stored)
        await db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # Get user for new token claims
    user_result = await db.execute(
        select(User).where(User.id == stored.user_id)
    )
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
    import hashlib

    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()

    await db.execute(
        delete(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    await db.commit()
```

- [ ] **Step 2: Verify router imports**

```bash
uv run python -c "from resume_builder.api.v1.endpoints.auth import auth_router; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 3: Commit**

```bash
git add src/resume_builder/api/v1/endpoints/auth.py
git commit -m "feat: add auth endpoints (register, login, refresh, logout)"
```

---

### Task 8: Create SQLSessionStore

**Files:**
- Create: `src/resume_builder/api/stores/sql_store.py`

**Interfaces:**
- Consumes: `SessionStore` ABC, `AsyncSessionLocal`, `Session` ORM model, `InteractiveResumeState` model, `SessionSummary` dataclass
- Produces: `SQLSessionStore(SessionStore)` — full implementation of the ABC

- [ ] **Step 1: Write stores/sql_store.py**

```python
"""SQLite-based session store — implements SessionStore ABC."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from resume_builder.api.core.database import AsyncSessionLocal
from resume_builder.api.models.session import Session
from resume_builder.api.stores.base import SessionStore, SessionSummary
from resume_builder.logger import get_logger
from resume_builder.models import InteractiveResumeState

logger = get_logger(__name__)


class SQLSessionStore(SessionStore):
    """Persists InteractiveResumeState as JSON in SQLite."""

    async def get(self, user_id: str, session_id: str) -> InteractiveResumeState | None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Session).where(
                    Session.user_id == user_id, Session.id == session_id
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return InteractiveResumeState.model_validate_json(row.state_json)

    async def save(
        self, user_id: str, session_id: str, state: InteractiveResumeState
    ) -> None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Session).where(
                    Session.user_id == user_id, Session.id == session_id
                )
            )
            row = result.scalar_one_or_none()
            state_json = state.model_dump_json()

            if row is not None:
                row.state_json = state_json
                row.updated_at = datetime.now(UTC)
            else:
                db.add(
                    Session(
                        id=session_id,
                        user_id=user_id,
                        state_json=state_json,
                    )
                )
            await db.commit()
            logger.debug("Saved session %s for user %s", session_id, user_id)

    async def list(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> tuple[list[SessionSummary], int]:
        async with AsyncSessionLocal() as db:
            # Total count
            count_result = await db.execute(
                select(func.count()).select_from(Session).where(
                    Session.user_id == user_id
                )
            )
            total = count_result.scalar() or 0

            # Page
            result = await db.execute(
                select(Session)
                .where(Session.user_id == user_id)
                .order_by(Session.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )
            rows = result.scalars().all()

            summaries: list[SessionSummary] = []
            for row in rows:
                try:
                    state = InteractiveResumeState.model_validate_json(row.state_json)
                except Exception:
                    continue
                wrk = state.working_resume
                contact = wrk.contact if wrk else None
                summaries.append(
                    SessionSummary(
                        session_id=row.id,
                        candidate_name=contact.name if contact else "Unnamed",
                        skills_count=len(wrk.skills) if wrk else 0,
                        experience_count=len(wrk.experience) if wrk else 0,
                        job_count=len(state.parsed_job_postings),
                        tailored_count=len(state.tailored_resumes),
                        last_updated=row.updated_at.isoformat(),
                    )
                )

            return summaries, total

    async def delete(self, user_id: str, session_id: str) -> bool:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                delete(Session).where(
                    Session.user_id == user_id, Session.id == session_id
                )
            )
            await db.commit()
            deleted = result.rowcount > 0
            if deleted:
                logger.debug("Deleted session %s for user %s", session_id, user_id)
            return deleted
```

- [ ] **Step 2: Verify the implementation**

```bash
uv run python -c "from resume_builder.api.stores.sql_store import SQLSessionStore; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 3: Commit**

```bash
git add src/resume_builder/api/stores/sql_store.py
git commit -m "feat: add SQLSessionStore — SQLite-backed SessionStore implementation"
```

---

### Task 9: Wire Everything Together

**Files:**
- Modify: `src/resume_builder/api/deps.py` — replace `get_default_user_id` with `get_current_user_id`
- Modify: `src/resume_builder/api/main.py` — call `init_db()` in lifespan
- Modify: `src/resume_builder/api/v1/router.py` — mount `auth_router`
- Modify: `src/resume_builder/api/services/session_service.py` — nothing (uses `SessionStore` ABC, wiring happens in deps.py)

**Interfaces:**
- Consumes: All previous tasks
- Produces: Working end-to-end auth + SQLite-backed sessions

- [ ] **Step 1: Update deps.py — replace get_default_user_id with get_current_user_id**

Replace the entire content of `deps.py`:

```python
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
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

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
```

- [ ] **Step 2: Update main.py — add init_db() to lifespan**

Add `from resume_builder.api.core.database import init_db` to imports, and call `await init_db()` after `create_worker_pool(...)`.

In the `lifespan` function, after line `create_worker_pool(max_workers=settings.api_max_workers)`, add:

```python
    await init_db()
```

The full lifespan becomes:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create worker pool, init DB. Shutdown: drain and destroy pool."""
    settings = get_api_settings()
    create_worker_pool(max_workers=settings.api_max_workers)
    await init_db()
    logger.info("API server started (workers=%d)", settings.api_max_workers)
    yield
    await shutdown_worker_pool()
    logger.info("API server shut down")
```

And add the import at the top:

```python
from resume_builder.api.core.database import init_db
```

- [ ] **Step 3: Update router.py — mount auth_router**

Add `auth` to the endpoint imports and mount the router. The `router.py` imports change from:

```python
from resume_builder.api.v1.endpoints import (
    conversation,
    jobs,
    resume,
    sessions,
    tailoring,
)
```

to:

```python
from resume_builder.api.v1.endpoints import (
    auth,
    conversation,
    jobs,
    resume,
    sessions,
    tailoring,
)
```

And add after the existing `include_router` lines:

```python
api_router.include_router(auth.auth_router)
```

Note: auth_router already has `prefix="/auth"` defined internally, so no prefix needed here.

- [ ] **Step 4: Verify the full import chain**

```bash
uv run python -c "
from resume_builder.api.main import create_app
app = create_app()
print('App created OK')
# Check all routes are registered
routes = [r.path for r in app.routes if hasattr(r, 'path')]
assert '/api/v1/auth/register' in routes
assert '/api/v1/auth/login' in routes
assert '/api/v1/auth/refresh' in routes
assert '/api/v1/auth/logout' in routes
assert '/api/v1/sessions' in routes
print('All routes registered')
"
```

Expected: prints `App created OK` then `All routes registered`.

- [ ] **Step 5: Run existing tests to confirm no regressions**

```bash
uv run pytest
```

Expected: All existing tests pass (no auth-related failures — existing tests shouldn't hit the API with auth yet).

- [ ] **Step 6: Commit**

```bash
git add src/resume_builder/api/deps.py src/resume_builder/api/main.py src/resume_builder/api/v1/router.py
git commit -m "feat: wire auth into API — JWT dependency, init_db, auth router"
```

---

### Task 10: Generate SECRET_KEY and update .env

**Files:**
- Modify: `.env` (add API_SECRET_KEY)

- [ ] **Step 1: Generate a secret key**

```bash
uv run python -c "import secrets; print(f'API_SECRET_KEY={secrets.token_hex(32)}')"
```

Expected: prints `API_SECRET_KEY=<64 hex chars>`.

- [ ] **Step 2: Add the generated key to .env**

Add the output line to `.env`.

- [ ] **Step 3: Verify the key loads**

```bash
uv run python -c "from resume_builder.api.core.config import get_api_settings; s = get_api_settings(); assert len(s.api_secret_key) == 64; print('Secret key loaded OK')"
```

Expected: prints `Secret key loaded OK`.

- [ ] **Step 4: Commit**

```bash
# Do NOT commit .env. Instead, note in commit message.
git add -p  # only if there are other files to commit
# Or just document: add API_SECRET_KEY=<generated> to .env
```

*This step is documentation-only unless there are other changes to commit alongside.*

---

### Task 11: Integration Smoke Test

- [ ] **Step 1: Start the server in the background**

```bash
uv run serve &
sleep 3
```

- [ ] **Step 2: Register a user**

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass1234"}' | python -m json.tool
```

Expected: JSON with `access_token`, `refresh_token`, `token_type`. Save the tokens.

- [ ] **Step 3: Login**

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=testuser&password=testpass1234" | python -m json.tool
```

Expected: JSON with `access_token`, `refresh_token`.

- [ ] **Step 4: Create a session (authenticated)**

```bash
TOKEN="<access_token from step 2>"
curl -s -X POST http://localhost:8000/api/v1/sessions \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

Expected: JSON session object with `session_id`.

- [ ] **Step 5: List sessions (should show the created one)**

```bash
curl -s http://localhost:8000/api/v1/sessions \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

Expected: Array with the session.

- [ ] **Step 6: Verify unauthenticated request is rejected**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/sessions
```

Expected: `401`.

- [ ] **Step 7: Verify user isolation**

```bash
# Register a second user
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"otheruser","password":"otherpass5678"}' > /tmp/other.json
TOKEN2=$(python -c "import json; print(json.load(open('/tmp/other.json'))['access_token'])")

# Second user should see empty session list (not testuser's sessions)
curl -s http://localhost:8000/api/v1/sessions \
  -H "Authorization: Bearer $TOKEN2" | python -m json.tool
```

Expected: Empty array `[]`.

- [ ] **Step 8: Refresh token**

```bash
REFRESH=$(python -c "import json; print(json.load(open('/tmp/other.json'))['refresh_token'])")
curl -s -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH\"}" | python -m json.tool
```

Expected: New `access_token` and `refresh_token`.

- [ ] **Step 9: Stop the server**

```bash
kill %1
```

- [ ] **Step 10: Verify the DB was created**

```bash
ls -la data/resume_builder.db
```

Expected: File exists with non-zero size.

---

### Task 12: Clean Up FileSessionStore

**Files:**
- Modify: `src/resume_builder/api/deps.py` — already switched to `SQLSessionStore` in Task 9
- Delete: `src/resume_builder/api/stores/file_store.py` (optional — can keep as reference)

**Note:** `FileSessionStore` is no longer referenced by any code after Task 9. The `deps.py` now imports `SQLSessionStore`. The file can be deleted or kept as a reference implementation. For cleanliness, remove it.

- [ ] **Step 1: Remove FileSessionStore**

```bash
rm src/resume_builder/api/stores/file_store.py
```

- [ ] **Step 2: Verify nothing broke**

```bash
uv run python -c "from resume_builder.api.main import create_app; app = create_app(); print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 3: Commit**

```bash
git rm src/resume_builder/api/stores/file_store.py
git commit -m "refactor: remove FileSessionStore, now fully on SQLSessionStore"
```

---

## Verification Checklist

After all tasks are complete:

1. `uv run pytest` — all existing tests pass
2. `uv run serve` — server starts without errors
3. Register → returns tokens
4. Login → returns tokens
5. Unauthenticated requests → 401
6. Authenticated session CRUD → works, user-scoped
7. Two users see isolated sessions
8. Refresh token rotation works
9. Logout revokes refresh token
10. `data/resume_builder.db` exists with correct schema
