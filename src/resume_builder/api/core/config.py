"""API-specific settings, separate from the CLI settings singleton."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class ApiSettings(BaseSettings):
    """Settings for the FastAPI server.

    Uses env vars prefixed with API_ (e.g. API_KEYS, API_CORS_ORIGINS).
    Separate from the CLI settings module to avoid coupling.
    """

    api_max_workers: int = 2
    """Maximum concurrent LLM operations in the thread pool."""

    api_cors_origins: list[str] = ["http://localhost:5173"]
    """Allowed CORS origins. Defaults to Svelte dev server."""

    api_session_ttl_days: int = 7
    """Sessions older than this are pruned on list."""

    api_max_upload_size_mb: int = 10
    """Maximum upload size in megabytes."""

    api_task_result_ttl_seconds: int = 300
    """How long completed task results are held in memory (5 min default)."""

    api_secret_key: str = ""
    """Secret key for signing JWT tokens. Set via API_SECRET_KEY env var or .env."""

    api_db_path: str = "data/resume_builder.db"
    """Path to the SQLite database file."""

    api_access_token_expire_minutes: int = 15
    """JWT access token lifetime in minutes."""

    api_refresh_token_expire_days: int = 7
    """Refresh token lifetime in days."""

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }


@lru_cache
def get_api_settings() -> ApiSettings:
    """Return cached ApiSettings. Cache can be cleared for test overrides."""
    return ApiSettings()
