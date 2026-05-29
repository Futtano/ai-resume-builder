"""
repo_parsing_crew/tools.py
--------------------------
Tools for fetching GitHub repository information via the GitHub REST API.
"""

import base64

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from resume_builder.settings import settings


class GitHubListDirInput(BaseModel):
    repo: str = Field(description="GitHub repository in owner/repo format")
    path: str = Field(
        default="",
        description="Optional subdirectory path within the repo. Defaults to root.",
    )


class GitHubFileReadInput(BaseModel):
    repo: str = Field(description="GitHub repository in owner/repo format")
    file_path: str = Field(
        description="Path to the file within the repo, e.g. 'README.md' or 'src/main.py'"
    )


def _github_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if settings.gh_token:
        headers["Authorization"] = f"Bearer {settings.gh_token}"
    return headers


def _github_get(url: str) -> tuple[int, dict | list | None]:
    try:
        resp = requests.get(url, headers=_github_headers(), timeout=30)
        return resp.status_code, resp.json()
    except Exception as exc:
        return 0, {"error": str(exc)}


class GitHubListDirTool(BaseTool):
    """List directory contents of a GitHub repository."""

    name: str = "github_list_dir"
    description: str = (
        "List the contents of a directory in a GitHub repository. "
        "Use this to explore the repo structure before fetching specific files. "
        "Returns a formatted list of entries with type (file/dir), name, and size."
    )
    args_schema: type[BaseModel] = GitHubListDirInput

    def _run(self, repo: str, path: str = "") -> str:
        url = (
            f"https://api.github.com/repos/{repo}/contents/{path}"
            if path
            else f"https://api.github.com/repos/{repo}/contents"
        )
        status, data = _github_get(url)
        if status != 200:
            err = (
                data.get("message", str(data)) if isinstance(data, dict) else str(data)
            )  # type: ignore[union-attr]
            return f"[ERROR] Failed to list {repo}/{path or '/'}: {err}"

        if not isinstance(data, list):
            return f"[ERROR] Unexpected response listing {repo}/{path or '/'}"

        lines = []
        for entry in data:
            entry_type = entry.get("type", "?")
            name = entry.get("name", "?")
            if entry_type == "dir":
                lines.append(f"[dir]  {name}/")
            elif entry_type == "file":
                size = entry.get("size", 0)
                lines.append(f"[file] {name} ({size} bytes)")
            else:
                lines.append(f"[{entry_type}] {name}")
        return "\n".join(lines) if lines else f"(empty directory) {repo}/{path or '/'}"


class GitHubFileReadTool(BaseTool):
    """Fetch and decode a single file from a GitHub repository."""

    name: str = "github_file_read"
    description: str = (
        "Fetch the content of a specific file from a GitHub repository. "
        "Use this after exploring the repo structure with github_list_dir. "
        "Returns the decoded file content as a string."
    )
    args_schema: type[BaseModel] = GitHubFileReadInput

    def _run(self, repo: str, file_path: str) -> str:
        url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
        status, data = _github_get(url)
        if status != 200:
            err = (
                data.get("message", str(data)) if isinstance(data, dict) else str(data)
            )  # type: ignore[union-attr]
            return f"[ERROR] Failed to fetch {file_path} from {repo}: {err}"

        if not isinstance(data, dict):
            return f"[ERROR] Unexpected response fetching {file_path} from {repo}"

        try:
            content = base64.b64decode(data["content"]).decode("utf-8")
        except Exception as exc:
            return f"[ERROR] Failed to decode content of {file_path} from {repo}: {exc}"

        return content
