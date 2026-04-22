"""
test_job_processor.py
---------------------
Tests for JobProcessor (scraping and file loading).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from resume_builder.processors.job import JobProcessor


class TestJobProcessor:
    def test_from_file(self, tmp_path: Path) -> None:
        processor = JobProcessor()
        job_file = tmp_path / "job1.txt"
        content = "Job Posting 1"
        job_file.write_text(content)

        processor.from_file(job_file)
        assert len(processor.extracted) == 1
        assert processor.extracted[0] == content

    def test_from_directory(self, tmp_path: Path) -> None:
        processor = JobProcessor()
        jobs_dir = tmp_path / "jobs"
        jobs_dir.mkdir()
        (jobs_dir / "job1.txt").write_text("Job 1")
        (jobs_dir / "job2.txt").write_text("Job 2")
        (jobs_dir / "not_a_job.pdf").write_text("Not a job")

        processor.from_directory(jobs_dir)
        # Should only load .txt files, sorted
        assert len(processor.extracted) == 2
        assert processor.extracted[0] == "Job 1"
        assert processor.extracted[1] == "Job 2"

    @patch("resume_builder.processors.job.JobProcessor._scrape_url")
    def test_from_url(self, mock_scrape: MagicMock) -> None:
        processor = JobProcessor()
        mock_scrape.return_value = "Scraped Content"
        url = "https://example.com/job"

        processor.from_url(url)
        assert len(processor.extracted) == 1
        assert processor.extracted[0] == "Scraped Content"
        mock_scrape.assert_called_once_with(url)

    @patch("resume_builder.processors.job.JobProcessor._scrape_url")
    def test_from_url_failure_logs_warning(self, mock_scrape: MagicMock) -> None:
        processor = JobProcessor()
        mock_scrape.side_effect = RuntimeError("Scrape failed")

        # Should not raise exception, just log and continue
        processor.from_url("https://fail.com")
        assert len(processor.extracted) == 0
