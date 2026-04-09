"""
test_flow.py
------------
Tests for ResumeBuilderFlow state management and validation.

No LLM calls — just testing the flow's plumbing.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from resume_builder.flow import ResumeBuilderFlow


class TestFlowInit:
    def test_requires_resume_source(self) -> None:
        """Flow must have either resume_pdf_path or resume_text."""
        with pytest.raises(ValueError, match="exactly one resume source"):
            ResumeBuilderFlow()

    def test_requires_job_postings(self) -> None:
        """Flow must have at least one job posting."""
        with pytest.raises(ValueError, match="Provide at least one job posting"):
            ResumeBuilderFlow(resume_text="text")

    def test_rejects_both_resume_sources(self) -> None:
        """Flow must not accept both resume_pdf_path AND resume_text."""
        with pytest.raises(ValueError, match="not both"):
            ResumeBuilderFlow(
                resume_pdf_path=Path("/tmp/x.pdf"),
                resume_text="text",
            )

    def test_accepts_resume_text_and_jobs(self) -> None:
        flow = ResumeBuilderFlow(
            resume_text="John Smith\nEngineer\nSkills: Python",
            job_postings=["Job 1 text"],
        )
        assert flow.state.total_jobs == 1
        assert flow.state.job_postings_raw == ["Job 1 text"]

    def test_accepts_multiple_jobs(self) -> None:
        flow = ResumeBuilderFlow(
            resume_text="Resume text",
            job_postings=["Job A", "Job B", "Job C"],
        )
        assert flow.state.total_jobs == 3

    def test_copies_job_postings(self) -> None:
        """Flow should copy the list, not mutate the original."""
        jobs = ["Job A"]
        flow = ResumeBuilderFlow(resume_text="text", job_postings=jobs)
        jobs.append("Job B")  # mutate original
        assert flow.state.job_postings_raw == ["Job A"]  # flow unaffected


class TestFlowProgress:
    def test_on_progress_callback(self) -> None:
        """Verify the on_progress callback is called."""
        calls: list[tuple[str, int, int]] = []

        flow = ResumeBuilderFlow(
            resume_text="Test resume",
            job_postings=["Test job"],
            on_progress=lambda msg, done, total: calls.append((msg, done, total)),
        )

        flow._emit_progress("Starting", 0, 1)
        assert len(calls) == 1
        assert calls[0] == ("Starting", 0, 1)


class TestFlowStepValidation:
    """Test individual flow step validation without running the full flow."""

    def test_crew_requires_parsed_resume(self) -> None:
        """_run_crew_for_job should fail if parsed_resume is None."""
        flow = ResumeBuilderFlow(resume_text="text", job_postings=["job"])
        flow.state.parsed_resume = None  # simulate not yet parsed

        with pytest.raises(RuntimeError, match="state.parsed_resume is None"):
            flow._run_crew_for_job("job text", 0)
