"""
config.py
---------
Centralised application configuration using pydantic-settings.

All settings have sensible defaults and can be overridden via environment
variables (or a .env file). Import the singleton `settings` wherever
configuration is needed — never read os.environ directly in application code.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM models ────────────────────────────────────────────────────
    writer_model: str = Field(
        default="gpt-4o",
        description="Model used for writing + review tasks (quality-critical)",
    )
    analyst_model: str = Field(
        default="gpt-4o-mini",
        description="Model used for parsing + analysis tasks (cost-optimised)",
    )

    # ── Output ────────────────────────────────────────────────────────
    output_dir: Path = Field(default=Path("./outputs"))

    # ── CrewAI behaviour ─────────────────────────────────────────────
    crewai_verbose: bool = False
    max_concurrent_jobs: int = Field(
        default=3,
        description="Max parallel resume-generation jobs in the thread pool",
    )

    # ── Resilience ────────────────────────────────────────────────────
    llm_max_retries: int = Field(
        default=3,
        description="Max retries on transient LLM failures",
    )
    llm_retry_base_delay: float = Field(
        default=2.0,
        description="Base delay (seconds) for exponential backoff on LLM retries",
    )

    @field_validator("output_dir", mode="before")
    @classmethod
    def resolve_output_dir(cls, v: object) -> Path:
        return Path(str(v)).resolve()


# Module-level singleton — import this everywhere
settings = Settings()
