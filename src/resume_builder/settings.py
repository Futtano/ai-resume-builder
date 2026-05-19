"""
config.py
---------
Centralised application configuration using pydantic-settings.

All settings have sensible defaults and can be overridden via environment
variables (or a .env file). Import the singleton `settings` wherever
configuration is needed — never read os.environ directly in application code.
"""

from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Output ────────────────────────────────────────────────────────
    output_dir: Path = Field(default=Path("outputs/"))

    # ── Logging ───────────────────────────────────────────────────────
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR",
    )

    # ── CrewAI behaviour ─────────────────────────────────────────────
    crewai_verbose: bool = False

    # ── API Keys ────────────────────────────────────────────────────
    gh_token: str | None = Field(
        default=None,
        description="Token authenticate with the GitHub API (to scrape projects)",
    )

    @field_validator("output_dir", mode="before")
    @classmethod
    def resolve_output_dir(cls, v: object) -> Path:
        return Path(str(v)).resolve()

    # ------------------------------------------------------------------
    # Factory helpers — use these when creating Agents
    # ------------------------------------------------------------------


# Module-level singleton — import this everywhere
settings = Settings()
