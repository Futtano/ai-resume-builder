"""
test_cli.py
-----------
Tests for the Typer CLI entry point.

Uses typer.CliRunner to invoke the CLI without spawning a real process.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from resume_builder.main import app

runner = CliRunner()


class TestCLIValidation:
    def test_no_arguments_errors(self) -> None:
        """Running without any options should error."""
        result = runner.invoke(app, ["run"])
        assert result.exit_code != 0

    def test_no_resume_errors(self, tmp_path: Path) -> None:
        """Missing resume positional argument should error."""
        job_file = tmp_path / "job.txt"
        job_file.write_text("Job posting")

        result = runner.invoke(app, ["run", "--job-files", str(job_file)])
        assert result.exit_code != 0

    def test_no_jobs_errors(self, tmp_path: Path) -> None:
        """Missing --job-files / --jobs-dir / --job-urls should error."""
        resume_file = tmp_path / "resume.pdf"
        resume_file.write_text("fake pdf")

        result = runner.invoke(app, ["run", str(resume_file)])
        assert result.exit_code != 0
        lower = result.output.lower()
        assert any(w in lower for w in ["job", "error", "provide"])

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
            str(resume_file),
            "--jobs-dir", str(jobs_dir),
        ])
        assert "Provide job postings" not in result.output
        assert "No job postings" not in result.output


class TestGitHubNormalization:
    def test_normalize_full_url(self) -> None:
        from resume_builder.main import _normalize_github_repo

        assert _normalize_github_repo("https://github.com/owner/repo") == "owner/repo"

    def test_normalize_full_url_trailing_slash(self) -> None:
        from resume_builder.main import _normalize_github_repo

        assert _normalize_github_repo("https://github.com/owner/repo/") == "owner/repo"

    def test_normalize_owner_repo(self) -> None:
        from resume_builder.main import _normalize_github_repo

        assert _normalize_github_repo("owner/repo") == "owner/repo"

    def test_normalize_www_url(self) -> None:
        from resume_builder.main import _normalize_github_repo

        assert _normalize_github_repo("https://www.github.com/owner/repo") == "owner/repo"
