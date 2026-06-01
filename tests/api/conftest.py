"""Shared fixtures for API tests.

All external LLM / CrewAI calls are mocked at the session level so no test
ever hits a real API.  Individual tests can configure the mock instances
via the ``mock_llm`` / ``mock_crews`` fixtures or override them with
additional ``mocker.patch`` / ``unittest.mock.patch`` calls.
"""

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


# ── Session-scoped external service mocks ────────────────────────
# These persist for the entire test run so that fire-and-forget
# background tasks (asyncio.create_task) never hit real APIs even
# after a test function's own ``with patch()`` block exits.


@pytest.fixture(scope="session", autouse=True)
def _mock_external_services_globally():
    """Replace LLM + CrewAI classes in session_service with MagicMocks.

    Session scope guarantees the mocks are active for the entire test
    run, including any background tasks spawned via asyncio.create_task
    that execute on the shared thread pool after the test returns.
    """
    import resume_builder.api.services.session_service as svc

    # Save originals for teardown
    _originals = {
        "LLM": svc.LLM,
        "JobParsingCrew": svc.JobParsingCrew,
        "RepoParsingCrew": svc.RepoParsingCrew,
        "ResumeParsingCrew": svc.ResumeParsingCrew,
        "ResumeBuilderCrew": svc.ResumeBuilderCrew,
    }

    # Replace LLM with a mock class whose instances are also mocks
    mock_llm_cls = MagicMock(name="LLM_class")
    mock_llm_instance = MagicMock(name="LLM_instance")
    mock_llm_instance.call.return_value = '{"skills": ["Python"]}'
    mock_llm_cls.return_value = mock_llm_instance

    mock_job_crew = MagicMock(name="JobParsingCrew")
    mock_repo_crew = MagicMock(name="RepoParsingCrew")
    mock_resume_crew = MagicMock(name="ResumeParsingCrew")
    mock_builder_crew = MagicMock(name="ResumeBuilderCrew")

    svc.LLM = mock_llm_cls  # type: ignore[invalid-assignment]
    svc.JobParsingCrew = mock_job_crew  # type: ignore[invalid-assignment]
    svc.RepoParsingCrew = mock_repo_crew  # type: ignore[invalid-assignment]
    svc.ResumeParsingCrew = mock_resume_crew  # type: ignore[invalid-assignment]
    svc.ResumeBuilderCrew = mock_builder_crew  # type: ignore[invalid-assignment]

    yield {
        "LLM_class": mock_llm_cls,
        "LLM_instance": mock_llm_instance,
        "JobParsingCrew": mock_job_crew,
        "RepoParsingCrew": mock_repo_crew,
        "ResumeParsingCrew": mock_resume_crew,
        "ResumeBuilderCrew": mock_builder_crew,
    }

    # Restore originals
    svc.LLM = _originals["LLM"]
    svc.JobParsingCrew = _originals["JobParsingCrew"]
    svc.RepoParsingCrew = _originals["RepoParsingCrew"]
    svc.ResumeParsingCrew = _originals["ResumeParsingCrew"]
    svc.ResumeBuilderCrew = _originals["ResumeBuilderCrew"]


@pytest.fixture
def mock_llm(_mock_external_services_globally):
    """Per-test access to the mock LLM instance (call history is shared).

    Use this to configure ``mock_llm.call.return_value`` or
    ``mock_llm.call.side_effect`` for a specific test.
    """
    instance = _mock_external_services_globally["LLM_instance"]
    instance.call.reset_mock()
    return instance


@pytest.fixture
def mock_crews(_mock_external_services_globally):
    """Per-test access to mock crew classes (call history is shared).

    Returns a namespace with ``JobParsingCrew``, ``RepoParsingCrew``,
    ``ResumeParsingCrew``, and ``ResumeBuilderCrew``.
    """
    from types import SimpleNamespace

    crews = SimpleNamespace(
        job=_mock_external_services_globally["JobParsingCrew"],
        repo=_mock_external_services_globally["RepoParsingCrew"],
        resume_parsing=_mock_external_services_globally["ResumeParsingCrew"],
        resume_builder=_mock_external_services_globally["ResumeBuilderCrew"],
    )
    for name in ("job", "repo", "resume_parsing", "resume_builder"):
        getattr(crews, name).reset_mock()
    return crews


# ── Store & client ───────────────────────────────────────────────


@pytest.fixture
def store(tmp_path):
    """Isolated FileSessionStore for direct state manipulation in tests."""
    from resume_builder.api.stores.file_store import FileSessionStore

    return FileSessionStore(base_dir=tmp_path / "uploads")


@pytest_asyncio.fixture
async def client(store):
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
    """Return a MagicMock whose ``.pydantic`` attribute holds *pydantic_obj*."""
    output = MagicMock()
    output.pydantic = pydantic_obj
    return output
