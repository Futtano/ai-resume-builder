"""
github_scraper.py
-----------------
GitHub repository scraper.

Given a list of GitHub repo URLs, searches each repo for:
- README content (description, features, usage)
- Dependency files (requirements.txt, pyproject.toml, package.json, etc.)

Returns raw search results for a downstream LLM agent to structure.
"""

# import os
import requests
import base64
from dataclasses import dataclass, field

from resume_builder.logger import get_logger
from resume_builder.config import settings

logger = get_logger(__name__)


@dataclass
class RepoScrapeResult:
    """Raw search results for a single GitHub repository."""

    repo: str  # e.g. "owner/repo"
    queries: dict[str, str] = field(default_factory=dict)


class GitHubScraper:
    """Scrape projects info using GitHub APIs"""

    def __init__(self) -> None:
        self._scraped: list[RepoScrapeResult] = []

    @property
    def scraped(self) -> list[RepoScrapeResult]:
        return self._scraped

    def get_branch_files(self, repo: str, branch: str = "main") -> str:
        files = ""
        url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
        response = self._fetch_gh_api(url=url)
        if response:
            if response.status_code == 200:
                data = response.json()
                files = " ".join(
                    [
                        item["path"]
                        for item in data.get("tree", [])
                        if item["type"] == "blob"
                    ]
                )
                self._add_scraped(repo=repo, queries={f"{branch}/files": files})
            else:
                logger.warning(
                    f"GitHub API respondend with {response.status_code} status_code. Returning empty file list."
                )
        else:
            logger.error("Invalid response from GitHub API. Returning empty file list.")

        return files

    def get_file_content(self, repo: str, file_path: str) -> str:
        url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
        response = self._fetch_gh_api(url=url)
        content = ""
        if response:
            if response.status_code == 200:
                data = response.json()
                content = base64.b64decode(data["content"]).decode("utf-8")
                self._add_scraped(repo=repo, queries={f"{file_path}/content": content})
            else:
                logger.warning(
                    f"GitHub API respondend with {response.status_code} status_code. Returning empty string."
                )
        else:
            logger.error("Invalid response from GitHub API. Returning empty string.")
        return content

    def scrape_repos(
        self, repos: list[str], files: list[str] = ["README.md", "pyproject.toml"]
    ) -> list[RepoScrapeResult]:
        for repo in repos:
            for file in files:
                self.get_file_content(repo=repo, file_path=file)
        return self.scraped

    def _fetch_gh_api(self, url: str) -> requests.Response | None:

        try:
            response = requests.get(
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {settings.gh_token}",
                },
            )
            return response
        except Exception as e:
            logger.error(f"Error while fetching GitHub API: {str(e)}")

    def _add_scraped(self, repo: str, queries: dict[str, str]) -> None:
        for scrape_result in self._scraped:
            if repo == scrape_result.repo:
                scrape_result.queries.update(queries)
                break
        else:
            self._scraped.append(RepoScrapeResult(repo=repo, queries=queries))


if __name__ == "__main__":
    scraper = GitHubScraper()
    scraper.scrape_repos(repos=["Futtano/ames-mlproject", "Futtano/ai-resume-builder"])
    # pprint(f"{scraper}: returned {files}")
    # pprint(f"{scraper}: returned {readme_content}")

    print(
        f"len(scraped): {len(scraper.scraped)}",
        f"len(scraped[0].queries): {len(scraper.scraped[0].queries)}",
        f"keys of scraped[0].queries: {scraper.scraped[0].queries.keys()}",
        sep="\n",
    )
