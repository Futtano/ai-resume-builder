"""
test_flow.py
------------
Tests for ResumeBuilderFlow state management and validation.

No LLM calls — just testing the flow's plumbing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from resume_builder.flow import ResumeBuilderFlow


class TestFlowInit:
    def test_requires_job_sources(self) -> None:
        """Flow must have at least one job file or URL."""
        with pytest.raises(ValueError, match="Provide at least one job posting"):
            ResumeBuilderFlow(
                resume_path=Path("resume.pdf"),
                job_files=[],
                job_urls=[],
            )

    def test_accepts_file_inputs(self) -> None:
        flow = ResumeBuilderFlow(
            resume_path=Path("resume.pdf"),
            job_files=[Path("job1.txt")],
        )
        assert flow.state.total_jobs == 1
        assert flow.state.job_files == [Path("job1.txt")]

    def test_accepts_url_inputs(self) -> None:
        flow = ResumeBuilderFlow(
            resume_path=Path("resume.pdf"),
            job_urls=["https://example.com/job"],
        )
        assert flow.state.total_jobs == 1
        assert flow.state.job_urls == ["https://example.com/job"]

    def test_accepts_mixed_inputs(self) -> None:
        flow = ResumeBuilderFlow(
            resume_path=Path("resume.pdf"),
            job_files=[Path("job1.txt"), Path("job2.txt")],
            job_urls=["https://example.com/job"],
        )
        assert flow.state.total_jobs == 3

    def test_total_jobs_is_combined(self) -> None:
        flow = ResumeBuilderFlow(
            resume_path=Path("resume.pdf"),
            job_files=[Path("a.txt"), Path("b.txt")],
            job_urls=["url1", "url2", "url3"],
        )
        assert flow.state.total_jobs == 5

    def test_copies_job_lists(self) -> None:
        """Flow should copy the lists, not mutate the original."""
        files = [Path("a.txt")]
        urls = ["url1"]
        flow = ResumeBuilderFlow(
            resume_path=Path("resume.pdf"),
            job_files=files,
            job_urls=urls,
        )
        files.append(Path("b.txt"))
        urls.append("url2")
        assert flow.state.job_files == [Path("a.txt")]
        assert flow.state.job_urls == ["url1"]

    def test_accepts_projects(self) -> None:
        flow = ResumeBuilderFlow(
            resume_path=Path("resume.pdf"),
            job_files=[Path("job.txt")],
            projects=["owner/repo1", "owner/repo2"],
        )
        assert flow.state.projects == ["owner/repo1", "owner/repo2"]


class TestFlowProgress:
    def test_on_progress_callback(self) -> None:
        """Verify the on_progress callback is called."""
        calls: list[tuple[str, int, int]] = []

        flow = ResumeBuilderFlow(
            resume_path=Path("resume.pdf"),
            job_files=[Path("test.txt")],
            on_progress=lambda msg, done, total: calls.append((msg, done, total)),
        )

        flow._emit_progress("Starting", 0, 1)
        assert len(calls) == 1
        assert calls[0] == ("Starting", 0, 1)
