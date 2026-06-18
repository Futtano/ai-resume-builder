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

_TEST_USER_ID = "default"

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


# ── In-memory SQLite + client ────────────────────────────────────


@pytest_asyncio.fixture
async def client():
    """Async test client with auth bypassed and in-memory SQLite DB.

    Overrides get_current_user_id to return a hardcoded test user ID,
    and forces the database engine to use in-memory SQLite.
    """
    import os

    # Set in-memory DB path before any database imports happen
    os.environ["API_DB_PATH"] = ":memory:"

    from resume_builder.api.core.database import reset_db

    reset_db()

    from resume_builder.api.deps import get_current_user_id
    from resume_builder.api.main import create_app

    app = create_app()

    # Bypass auth: always return a test user ID
    def _bypass_auth():
        return _TEST_USER_ID

    app.dependency_overrides[get_current_user_id] = _bypass_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        async with app.router.lifespan_context(app):
            yield ac


# ── Store (shares the same in-memory DB as client) ──


@pytest.fixture
def store():
    """SQLSessionStore backed by the same in-memory SQLite DB as the client."""
    from resume_builder.api.stores.sql_store import SQLSessionStore

    return SQLSessionStore()


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
