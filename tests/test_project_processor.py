"""
test_project_processor.py
-------------------------
Tests for ProjectProcessor (GitHub scraping and Markdown formatting).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from resume_builder.processors.project import ProjectProcessor, RepoScrapeResult


class TestProjectProcessor:
    def test_repo_scrape_result_to_markdown(self) -> None:
        result = RepoScrapeResult(
            repo="user/repo",
            queries={
                "README.md": "README content",
                "pyproject.toml": "toml content",
            },
        )
        md = result.to_markdown()
        assert "# Repository: user/repo" in md
        assert "## README.md\nREADME content" in md
        assert "## pyproject.toml\ntoml content" in md

    @patch("resume_builder.processors.project.ProjectProcessor._get_file_content")
    def test_from_github(self, mock_get_content: MagicMock) -> None:
        processor = ProjectProcessor()
        mock_get_content.side_effect = lambda repo, path: f"Content of {path} in {repo}"

        processor.from_github(["user/repo1", "user/repo2"])

        assert len(processor.extracted) == 2
        assert "# Repository: user/repo1" in processor.extracted[0]
        assert "## README.md\nContent of README.md in user/repo1" in processor.extracted[0]
        assert "# Repository: user/repo2" in processor.extracted[1]

    @patch("resume_builder.processors.project.ProjectProcessor._get_file_content")
    def test_from_github_skips_empty_repos(self, mock_get_content: MagicMock) -> None:
        processor = ProjectProcessor()
        mock_get_content.return_value = None  # No files found

        processor.from_github(["user/empty"])
        assert len(processor.extracted) == 0
