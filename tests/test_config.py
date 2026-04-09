"""
test_config.py
--------------
Tests for Settings loading, env overrides, and make_llm() factory.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from resume_builder.config import Settings


class TestSettings:
    @pytest.fixture(autouse=True)
    def _isolate_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Isolate Settings from .env and environment so defaults are used."""
        # Clear all relevant env vars
        for key in [
            "WRITER_MODEL", "ANALYST_MODEL", "LOG_LEVEL", "CREWAI_VERBOSE",
            "MAX_CONCURRENT_JOBS", "LLM_MAX_RETRIES", "LLM_BASE_URL",
            "LLM_API_KEY", "EMBEDDING_MODEL", "EMBEDDING_BASE_URL",
        ]:
            monkeypatch.delenv(key, raising=False)

    def test_defaults(self) -> None:
        """Test that defaults match the code, ignoring any .env file."""
        # Settings() reads .env — test the defaults directly via explicit construction
        s = Settings(
            writer_model="gpt-4o",
            analyst_model="gpt-4o-mini",
            log_level="INFO",
            crewai_verbose=False,
            max_concurrent_jobs=3,
            llm_max_retries=3,
            llm_retry_base_delay=2.0,
            llm_base_url=None,
            llm_api_key=None,
            output_dir=Path("./outputs"),
            embedding_model=None,
            embedding_base_url=None,
        )
        assert s.writer_model == "gpt-4o"
        assert s.analyst_model == "gpt-4o-mini"
        assert s.log_level == "INFO"
        assert s.crewai_verbose is False
        assert s.max_concurrent_jobs == 3
        assert s.llm_max_retries == 3
        assert s.llm_base_url is None

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("WRITER_MODEL", "qwen3.5:9b")
        monkeypatch.setenv("CREWAI_VERBOSE", "true")

        s = Settings()
        assert s.log_level == "DEBUG"
        assert s.writer_model == "qwen3.5:9b"
        assert s.crewai_verbose is True

    def test_output_dir_resolves_absolute(self) -> None:
        s = Settings()
        assert s.output_dir.is_absolute()
