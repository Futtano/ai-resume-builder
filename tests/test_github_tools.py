"""
test_github_tools.py
--------------------
Tests for GitHubListDirTool and GitHubFileReadTool.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from resume_builder.crews.repo_parsing_crew.tools import (
    GitHubListDirTool,
    GitHubFileReadTool,
)


GITHUB_API = "https://api.github.com"


class TestGitHubListDirTool:
    def test_tool_metadata(self) -> None:
        tool = GitHubListDirTool()
        assert tool.name == "github_list_dir"

    @patch("resume_builder.crews.repo_parsing_crew.tools.requests.get")
    def test_list_root_success(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"type": "dir", "name": "src", "size": 0},
            {"type": "file", "name": "README.md", "size": 2048},
            {"type": "file", "name": "pyproject.toml", "size": 512},
        ]
        mock_get.return_value = mock_resp

        tool = GitHubListDirTool()
        output = tool._run("owner/repo")

        assert "[dir]  src/" in output
        assert "[file] README.md (2048 bytes)" in output
        assert "[file] pyproject.toml (512 bytes)" in output

    @patch("resume_builder.crews.repo_parsing_crew.tools.requests.get")
    def test_list_subdirectory(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"type": "file", "name": "__init__.py", "size": 100},
        ]
        mock_get.return_value = mock_resp

        tool = GitHubListDirTool()
        output = tool._run("owner/repo", "src")

        assert "[file] __init__.py (100 bytes)" in output

    @patch("resume_builder.crews.repo_parsing_crew.tools.requests.get")
    def test_list_not_found(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"message": "Not Found"}
        mock_get.return_value = mock_resp

        tool = GitHubListDirTool()
        output = tool._run("owner/nonexistent")

        assert output.startswith("[ERROR]")
        assert "Not Found" in output

    @patch("resume_builder.crews.repo_parsing_crew.tools.requests.get")
    def test_list_network_error(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = ConnectionError("Network unreachable")

        tool = GitHubListDirTool()
        output = tool._run("owner/repo")

        assert output.startswith("[ERROR]")

    @patch("resume_builder.crews.repo_parsing_crew.tools.requests.get")
    def test_list_empty_directory(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_get.return_value = mock_resp

        tool = GitHubListDirTool()
        output = tool._run("owner/empty-repo")

        assert "empty directory" in output.lower()


class TestGitHubFileReadTool:
    def test_tool_metadata(self) -> None:
        tool = GitHubFileReadTool()
        assert tool.name == "github_file_read"

    @patch("resume_builder.crews.repo_parsing_crew.tools.requests.get")
    def test_fetch_success(self, mock_get: MagicMock) -> None:
        import base64

        content = "# Test Project\nA sample project."
        encoded = base64.b64encode(content.encode()).decode()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"content": encoded, "name": "README.md"}
        mock_get.return_value = mock_resp

        tool = GitHubFileReadTool()
        output = tool._run("owner/repo", "README.md")

        assert output == content

    @patch("resume_builder.crews.repo_parsing_crew.tools.requests.get")
    def test_fetch_not_found(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"message": "Not Found"}
        mock_get.return_value = mock_resp

        tool = GitHubFileReadTool()
        output = tool._run("owner/repo", "nonexistent.txt")

        assert output.startswith("[ERROR]")
        assert "Not Found" in output

    @patch("resume_builder.crews.repo_parsing_crew.tools.requests.get")
    def test_fetch_rate_limited(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = {"message": "API rate limit exceeded for ..."}
        mock_get.return_value = mock_resp

        tool = GitHubFileReadTool()
        output = tool._run("owner/repo", "README.md")

        assert output.startswith("[ERROR]")
        assert "rate limit" in output

    @patch("resume_builder.crews.repo_parsing_crew.tools.requests.get")
    def test_fetch_network_error(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = ConnectionError("Network unreachable")

        tool = GitHubFileReadTool()
        output = tool._run("owner/repo", "README.md")

        assert output.startswith("[ERROR]")
