"""API-specific settings, separate from the CLI settings singleton."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class ApiSettings(BaseSettings):
    """Settings for the FastAPI server.

    Uses env vars prefixed with API_ (e.g. API_KEYS, API_CORS_ORIGINS).
    Separate from the CLI settings module to avoid coupling.
    """

    api_keys: dict[str, str] = {}
    """Mapping of API key value -> user_id. Configure in .env as JSON dict."""

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

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }


@lru_cache
def get_api_settings() -> ApiSettings:
    """Return cached ApiSettings. Cache can be cleared for test overrides."""
    return ApiSettings()
