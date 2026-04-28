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

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from crewai import LLM

# Load .env with override=True so values always replace whatever is in the environment
load_dotenv(".env", override=True)


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

    # ── Custom LLM provider (e.g. Ollama) ─────────────────────────────
    llm_base_url: str | None = Field(
        default=None,
        description="Base URL for OpenAI-compatible endpoint (e.g. Ollama)",
    )
    llm_api_key: str | None = Field(
        default=None,
        description="API key for the LLM provider (can be empty for Ollama)",
    )

    # ── Embedding model ───────────────────────────────────────────────
    embedding_model: str | None = Field(
        default=None,
        description="Embedding model for memory/knowledge (e.g. 'ollama/qwen3-embedding:0.6b')",
    )
    embedding_base_url: str | None = Field(
        default=None,
        description="Base URL for OpenAI-compatible embeddings endpoint",
    )

    # ── Output ────────────────────────────────────────────────────────
    output_dir: Path = Field(default=Path("./outputs"))

    # ── Logging ───────────────────────────────────────────────────────
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR",
    )

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

    def make_llm(
        self,
        model: str,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int | None = None,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
    ) -> LLM:
        """Create an LLM instance with full parameter support."""
        kwargs: dict = {
            "model": model,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if self.llm_base_url:
            kwargs["base_url"] = self.llm_base_url
        if self.llm_api_key is not None:
            kwargs["api_key"] = self.llm_api_key
        return LLM(**kwargs)

    @property
    def analyst_llm(self) -> LLM:
        return self.make_llm(self.analyst_model, temperature=0.1, top_p=0.1)

    @property
    def writer_llm(self) -> LLM:
        return self.make_llm(self.writer_model, temperature=0.3, top_p=0.3)


# Module-level singleton — import this everywhere
settings = Settings()
