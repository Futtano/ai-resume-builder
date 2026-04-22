"""
project.py
----------
Processor for extracting and formatting GitHub repository information.
"""

from __future__ import annotations

import base64
import requests
from dataclasses import dataclass, field
from typing import Optional

from resume_builder.config import settings
from resume_builder.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RepoScrapeResult:
    """Raw search results for a single GitHub repository."""
    repo: str
    queries: dict[str, str] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Convert scraped data to a structured Markdown string."""
        sections = [f"# Repository: {self.repo}"]
        for query, content in self.queries.items():
            sections.append(f"## {query}\n{content}")
        return "\n\n".join(sections)


class ProjectProcessor:
    """
    Handles scraping GitHub repositories and formatting them as Markdown.
    """

    def __init__(self) -> None:
        self._scraped: list[RepoScrapeResult] = []

    @property
    def extracted(self) -> list[str]:
        """List of Markdown-formatted repository information."""
        return [res.to_markdown() for res in self._scraped]

    def from_github(
        self,
        repos: list[str],
        files: list[str] = ["README.md", "pyproject.toml"],
    ) -> ProjectProcessor:
        """Scrape multiple GitHub repositories."""
        for repo in repos:
            logger.info("Scraping GitHub repo: %s", repo)
            try:
                result = RepoScrapeResult(repo=repo)
                for file_path in files:
                    content = self._get_file_content(repo, file_path)
                    if content:
                        result.queries[file_path] = content

                if result.queries:
                    self._scraped.append(result)
                    logger.info("Scraped %d file(s) from %s", len(result.queries), repo)
                else:
                    logger.warning("No files found for repo: %s", repo)
            except Exception as exc:
                logger.warning("Failed to scrape GitHub repo %s: %s", repo, exc)
        return self

    def _get_file_content(self, repo: str, file_path: str) -> Optional[str]:
        """Fetch content of a specific file from a GitHub repo."""
        url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
        try:
            response = requests.get(
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {settings.gh_token}",
                },
            )
            if response.status_code == 200:
                data = response.json()
                return base64.b64decode(data["content"]).decode("utf-8")
            else:
                logger.debug(
                    "GitHub API returned %d for %s in %s",
                    response.status_code,
                    file_path,
                    repo,
                )
                return None
        except Exception as exc:
            logger.error("Error fetching %s from %s: %s", file_path, repo, exc)
            return None
