# User Authentication & Session Scoping — Design Spec

**Date:** 2026-06-18
**Status:** Approved
**Branch:** `feat/sessions`

## Context

The resume builder has a FastAPI backend with full session CRUD, but all requests use a hardcoded `user_id = "default"`. The `deps.py` file explicitly notes: *"auth removed — will be rebuilt later."* The frontend has a stubbed `login/+page.svelte` route. This feature adds username/password authentication and scopes sessions to individual users.

## Decisions

| Decision | Choice |
|---|---|
| Storage | SQLite via SQLAlchemy + aiosqlite (async) |
| Auth mechanism | JWT access tokens (15min) + opaque refresh tokens (7 days, rotated) |
| Registration | Open — anyone can sign up with username + password |
| CLI | Unchanged — auth is API + Frontend only |
| Migration | Full — sessions move from `FileSessionStore` to SQLite |

## Schema

### Users

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | Generated server-side |
| `username` | TEXT UNIQUE NOT NULL | 3–64 chars, case-insensitive |
| `password_hash` | TEXT NOT NULL | bcrypt via passlib |
| `created_at` | DATETIME (UTC) | |
| `updated_at` | DATETIME (UTC) | |

### Sessions

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | 8-char hex, compatible with existing format |
| `user_id` | UUID (FK → users.id) | NOT NULL, indexed |
| `state_json` | TEXT NOT NULL | `InteractiveResumeState.model_dump_json()` |
| `created_at` | DATETIME (UTC) | |
| `updated_at` | DATETIME (UTC) | |

### Refresh Tokens

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | |
| `user_id` | UUID (FK → users.id) | NOT NULL, indexed |
| `token_hash` | TEXT UNIQUE NOT NULL | SHA-256 of raw token |
| `expires_at` | DATETIME | |
| `created_at` | DATETIME | |

## Auth Endpoints (`/api/v1/auth`)

- `POST /auth/register` — body: `{username, password}` → `UserResponse` + `TokenResponse` (auto-login)
- `POST /auth/login` — form-encoded `username` + `password` → `TokenResponse`
- `POST /auth/refresh` — body: `{refresh_token}` → new `TokenResponse` (rotates refresh token)
- `POST /auth/logout` — body: `{refresh_token}` → `204` (deletes token from DB)

## Token Design

- **Access token**: JWT (HS256), claims: `sub` (user_id), `username`, `exp` (15min), `iat`
- **Refresh token**: Opaque 64-char hex, SHA-256 hashed in DB, 7-day expiry, rotated on each use
- Theft detection: if a revoked refresh token is reused, revoke all user's refresh tokens

## Auth Dependency

Replace `get_default_user_id()` → `get_current_user_id()` in `deps.py`:
- Extracts Bearer token from `Authorization` header
- Decodes JWT, returns `user_id` string
- Raises 401 if invalid/expired
- Same return type (`str`) — zero changes needed in endpoint code

## Files

### New

| File | Purpose |
|---|---|
| `api/core/database.py` | Async SQLAlchemy engine, session factory, `get_db`, `init_db` |
| `api/models/__init__.py` | Declarative `Base` |
| `api/models/user.py` | `User` ORM model |
| `api/models/session.py` | `Session` ORM model |
| `api/models/refresh_token.py` | `RefreshToken` ORM model |
| `api/auth/__init__.py` | Public exports |
| `api/auth/hashing.py` | `hash_password()`, `verify_password()` (passlib bcrypt) |
| `api/auth/tokens.py` | `create_access_token()`, `create_refresh_token()`, `decode_access_token()` |
| `api/stores/sql_store.py` | `SQLSessionStore` implementing `SessionStore` ABC |
| `api/v1/endpoints/auth.py` | Auth router (register, login, refresh, logout) |
| `api/schemas/auth.py` | Pydantic request/response schemas |

### Modified

| File | Change |
|---|---|
| `pyproject.toml` | Add `sqlalchemy[asyncio]`, `aiosqlite`, `passlib[bcrypt]`, `python-jose` |
| `api/core/config.py` | Add `SECRET_KEY`, `DB_PATH`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` |
| `api/main.py` | Call `init_db()` in lifespan startup |
| `api/deps.py` | Replace `get_default_user_id` with `get_current_user_id` |
| `api/v1/router.py` | Mount `auth.router` |
| `api/services/session_service.py` | Use `SQLSessionStore` instead of `FileSessionStore` |

### Unchanged

- All 5 endpoint files — `sessions.py`, `resume.py`, `jobs.py`, `tailoring.py`, `conversation.py`
- `InteractiveResumeState` model
- `SessionStore` ABC
- CLI code (`interactive_flow.py`, `main.py`)

## Implementation Order

1. Add dependencies (`uv add`)
2. Add settings fields to `ApiSettings`
3. Create `database.py` (engine, session factory, `init_db`)
4. Create SQLAlchemy models (User, Session, RefreshToken)
5. Create auth utilities (hashing.py, tokens.py)
6. Create auth schemas
7. Create auth endpoints
8. Create `SQLSessionStore`
9. Wire everything (deps.py, main.py lifespan, router, session_service)
10. Remove `FileSessionStore`

## Verification

1. `uv run pytest` — all existing tests pass
2. Register: `curl -X POST /api/v1/auth/register -H "Content-Type: application/json" -d '{"username":"alice","password":"secret1234"}'` → returns tokens
3. Login: `curl -X POST /api/v1/auth/login -d "username=alice&password=secret1234"` → returns tokens
4. Session CRUD: `curl -H "Authorization: Bearer <token>" /api/v1/sessions` → user-scoped
5. Isolation: create sessions as alice and bob, verify each sees only their own
6. Refresh: `curl -X POST /api/v1/auth/refresh -d '{"refresh_token":"..."}'` → new token pair
7. Logout: refresh token no longer works
