"""
test_config.py
--------------
Tests for Settings loading, env overrides, and make_llm() factory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from resume_builder.settings import Settings


class TestSettings:
    @pytest.fixture(autouse=True)
    def _isolate_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Isolate Settings from .env and environment so defaults are used."""
        for key in ["LOG_LEVEL", "CREWAI_VERBOSE", "GH_TOKEN"]:
            monkeypatch.delenv(key, raising=False)

    def test_defaults(self) -> None:
        s = Settings(
            log_level="INFO",
            crewai_verbose=False,
            output_dir=Path("./outputs"),
        )
        assert s.log_level == "INFO"
        assert s.crewai_verbose is False
        assert s.output_dir == Path("./outputs").resolve()

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("CREWAI_VERBOSE", "true")

        s = Settings()
        assert s.log_level == "DEBUG"
        assert s.crewai_verbose is True

    def test_output_dir_resolves_absolute(self) -> None:
        s = Settings()
        assert s.output_dir.is_absolute()

    def test_gh_token_defaults_to_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GH_TOKEN", "")
        s = Settings(gh_token=None)
        assert s.gh_token is None

    def test_gh_token_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GH_TOKEN", "ghp_test123")
        s = Settings()
        assert s.gh_token == "ghp_test123"
