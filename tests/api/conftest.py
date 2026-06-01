"""Shared fixtures for API tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from resume_builder.models import (
    ContactInfo,
    EducationEntry,
    ExperienceEntry,
    JobRequirements,
    ParsedResume,
)

TEST_API_KEY = "test-api-key-123"
TEST_USER_ID = "test-user"


def _make_test_settings():
    from resume_builder.api.core.config import ApiSettings

    return ApiSettings(
        api_keys={TEST_API_KEY: TEST_USER_ID},
        api_cors_origins=["*"],
    )


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch):
    from resume_builder.api.core import config as config_mod

    monkeypatch.setattr(config_mod, "get_api_settings", _make_test_settings)


@pytest.fixture
def store(tmp_path):
    """Isolated FileSessionStore for direct state manipulation in tests."""
    from resume_builder.api.stores.file_store import FileSessionStore

    return FileSessionStore(base_dir=tmp_path / "uploads")


@pytest_asyncio.fixture
async def client(tmp_path, store):
    """Async test client with store dependency overridden."""
    from resume_builder.api.deps import get_session_store
    from resume_builder.api.main import create_app

    app = create_app()

    def _override_store():
        return store

    app.dependency_overrides[get_session_store] = _override_store

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        async with app.router.lifespan_context(app):
            yield ac


@pytest.fixture
def auth_headers():
    return {"X-API-Key": TEST_API_KEY}


# ── Sample domain models ──


@pytest.fixture
def sample_parsed_resume():
    return ParsedResume(
        contact=ContactInfo(name="Alice Smith", email="alice@example.com"),
        professional_summary="Experienced software engineer.",
        experience=[
            ExperienceEntry(
                company="TechCorp",
                role="Senior Backend Engineer",
                start_date="2022-01",
                end_date="Present",
                bullets=["Built microservices"],
                skills_demonstrated=["Python", "Go"],
            )
        ],
        skills=["Python", "Go", "Docker"],
        education=[
            EducationEntry(
                institution="PoliMi",
                degree="Master's",
                field_of_study="Computer Science",
                start_date="2016",
                end_date="2020",
            )
        ],
        totals_yoe=5,
    )


@pytest.fixture
def sample_job() -> JobRequirements:
    return JobRequirements(
        job_title="Senior Backend Engineer",
        company="Acme Corp",
        seniority_level="Senior",
        required_skills=["Python", "Go", "AWS"],
        preferred_skills=["Rust"],
        key_responsibilities=["Build APIs", "Lead team"],
        ats_keywords=["microservices", "cloud"],
        industry="Tech",
        team_size="10-20",
        remote_policy="Hybrid",
    )


def mock_crew_output(pydantic_obj):
    output = MagicMock()
    output.pydantic = pydantic_obj
    return output
