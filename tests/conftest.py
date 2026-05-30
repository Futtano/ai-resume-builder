"""
conftest.py
-----------
Shared fixtures for the Resume Builder test suite.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from resume_builder.models import (
    ContactInfo,
    EducationEntry,
    ExperienceEntry,
    ParsedResume,
)


@pytest.fixture()
def tmp_dir():
    """Return a temporary directory (cleaned up after the test)."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture()
def sample_contact() -> ContactInfo:
    return ContactInfo(
        name="Alice Smith",
        email="alice@example.com",
        phone="+1-555-0100",
        location="Milan, Italy",
        linkedin="linkedin.com/in/alice",
        github="github.com/alice",
        portfolio="alice.dev",
    )


@pytest.fixture()
def sample_parsed_resume(sample_contact: ContactInfo) -> ParsedResume:
    return ParsedResume(
        contact=sample_contact,
        professional_summary="Experienced software engineer with 5+ years in backend systems.",
        experience=[
            ExperienceEntry(
                company="TechCorp",
                role="Senior Backend Engineer",
                start_date="Jan 2022",
                end_date="Present",
                location="Milan, Italy",
                bullets=[
                    "Designed microservices handling 10M+ daily requests",
                    "Led migration from monolith to Go-based services",
                ],
                skills_demonstrated=["Go", "Python", "Kubernetes"],
            ),
        ],
        skills=["Python", "Go", "Docker", "PostgreSQL", "Redis", "AWS"],
        education=[
            EducationEntry(
                institution="Politecnico di Milano",
                degree="Master's",
                field_of_study="Computer Science",
                start_date="2016",
                end_date="2020",
            ),
        ],
        certifications=["AWS Solutions Architect"],
        totals_yoe=5,
    )
