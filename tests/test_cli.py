"""
test_cli.py
-----------
Tests for the Typer CLI entry point.

Uses typer.CliRunner to invoke the CLI without spawning a real process.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from resume_builder.main import app

runner = CliRunner()


class TestCLIValidation:
    def test_no_arguments_errors(self) -> None:
        """Running without any options should error."""
        result = runner.invoke(app, ["run"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "Error" in result.output

    def test_no_resume_errors(self, tmp_path: Path) -> None:
        """Missing --resume should error."""
        job_file = tmp_path / "job.txt"
        job_file.write_text("Job posting")

        result = runner.invoke(app, ["run", "--jobs", str(job_file)])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "resume" in result.output.lower()

    def test_no_jobs_errors(self, tmp_path: Path) -> None:
        """Missing --jobs / --jobs-dir / --job-urls should error."""
        resume_file = tmp_path / "resume.pdf"
        resume_file.write_text("fake pdf")

        result = runner.invoke(app, ["run", "--resume", str(resume_file)])
        assert result.exit_code != 0
        # Error could mention "job postings" or "job-urls" or "jobs-dir"
        lower = result.output.lower()
        assert any(w in lower for w in ["job", "error", "provide"])

    def test_single_resume_only(self, tmp_path: Path) -> None:
        """CLI --resume takes exactly one file (Typer enforces this)."""
        resume1 = tmp_path / "r1.pdf"
        resume2 = tmp_path / "r2.pdf"
        resume1.write_text("r1")
        resume2.write_text("r2")

        # --resume can only be given once; passing it twice is a CLI error
        result = runner.invoke(app, [
            "run",
            "--resume", str(resume1),
            "--resume", str(resume2),
            "--jobs", str(tmp_path / "job.txt"),
        ])
        # Typer will reject duplicate option usage
        assert result.exit_code != 0

    def test_jobs_dir_option(self, tmp_path: Path) -> None:
        """--jobs-dir should load all .txt files from the directory."""
        resume_file = tmp_path / "resume.pdf"
        resume_file.write_text("fake pdf")

        jobs_dir = tmp_path / "jobs"
        jobs_dir.mkdir()
        (jobs_dir / "job1.txt").write_text("Job 1")
        (jobs_dir / "job2.txt").write_text("Job 2")

        result = runner.invoke(app, [
            "run",
            "--resume", str(resume_file),
            "--jobs-dir", str(jobs_dir),
        ])
        # Should not error on input validation (may fail later on LLM)
        # But at least it should get past the input validation stage
        assert "Provide job postings" not in result.output
