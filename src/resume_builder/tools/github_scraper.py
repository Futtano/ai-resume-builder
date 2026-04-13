"""
github_scraper.py
-----------------
GitHub repository scraper using CrewAI's GithubSearchTool.

Given a list of GitHub repo URLs, searches each repo for:
- README content (description, features, usage)
- Dependency files (requirements.txt, pyproject.toml, package.json, etc.)
- Architecture/design docs
- CI/CD and infrastructure configs

Returns raw search results for a downstream LLM agent to structure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from crewai_tools import GithubSearchTool

from resume_builder.config import settings
from resume_builder.logger import get_logger

logger = get_logger(__name__)

# Queries run against each repo to gather comprehensive context.
# Each query targets a different aspect of the project.
_REPO_QUERIES = [
    "README project description features overview usage",
    "requirements.txt pyproject.toml package.json go.mod Cargo.toml dependencies",
    "Dockerfile docker-compose docker infrastructure deployment",
    "architecture design how it works structure components",
    "API endpoints routes controllers services handlers",
    "CI CD GitHub Actions workflow pipeline tests Makefile",
]


@dataclass
class RepoSearchResults:
    """Raw search results for a single GitHub repository."""

    repo_name: str  # e.g. "owner/repo"
    queries: dict[str, str] = field(default_factory=dict)


def _parse_github_url(url: str) -> str:
    """Normalize a GitHub URL to the canonical repo URL.

    Handles:
        https://github.com/owner/repo
        https://github.com/owner/repo/
        https://github.com/owner/repo/tree/main
        git@github.com:owner/repo.git
    """
    url = url.rstrip("/")

    # Standard HTTPS — strip any trailing path segments
    match = re.search(r"(https://github\.com/[^/]+/[^/]+?)(?:/|$)", url)
    if match:
        return match.group(1)

    # SSH style → convert to HTTPS
    match = re.search(r"github\.com:([^/]+)/([^/]+?)(?:\.git)?$", url)
    if match:
        return f"https://github.com/{match.group(1)}/{match.group(2)}"

    raise ValueError(f"Not a valid GitHub repository URL: {url}")


def _build_tool_config() -> dict:
    """Build GithubSearchTool config using project settings.

    - LLM: uses the analyst model via the configured OpenAI-compatible endpoint
    - Embedder: uses local Ollama with nomic-embed-text for embeddings
    """
    return dict(
        llm=dict(
            provider="openai",
            config=dict(
                model=settings.analyst_model,
                api_base=settings.llm_base_url,
            ),
        ),
        embedding_model=dict(
            provider="ollama",
            config=dict(
                model_name=settings.embedding_model or "nomic-embed-text:latest",
                base_url=settings.embedding_base_url or "http://localhost:11434",
            ),
        ),
    )


def scrape_github_repos(
    repo_urls: list[str],
    gh_token: str = "",
) -> list[RepoSearchResults]:
    """
    Scrape multiple GitHub repos using semantic search.

    For each repo, runs several queries via GithubSearchTool
    to gather README content, dependency files, architecture docs, etc.

    Public repos work without a GitHub token (empty string is fine).

    Args:
        repo_urls: List of GitHub repository URLs.
        gh_token: GitHub Personal Access Token (empty for public repos).

    Returns:
        A list of RepoSearchResults, one per repo.
    """
    logger.info("Scraping %d GitHub repo(s)", len(repo_urls))
    tool_config = _build_tool_config()
    results: list[RepoSearchResults] = []

    for url in repo_urls:
        repo_url = _parse_github_url(url)
        # Extract owner/repo for logging
        match = re.search(r"github\.com/([^/]+/[^/]+?)(?:/|$)", repo_url)
        repo_name = match.group(1) if match else repo_url
        logger.info("Scraping repo: %s", repo_name)

        queries: dict[str, str] = {}

        for query in _REPO_QUERIES:
            try:
                tool = GithubSearchTool(
                    github_repo=repo_url,
                    gh_token=gh_token,
                    content_types=["code", "repo"],
                    collection_name=f"{settings.embedding_model}-collection",
                    config=tool_config,
                )
                search_result = tool._run(
                    search_query=query,
                    github_repo=repo_url,
                    content_types=["code", "repo"],
                    limit=5,
                )
                queries[query] = search_result or ""
                logger.debug(
                    "Query '%s' returned %d chars",
                    query,
                    len(search_result or ""),
                )
            except Exception as exc:
                logger.warning("Query '%s' failed for %s: %s", query, repo_name, exc)
                queries[query] = ""

        total_chars = sum(len(v) for v in queries.values())
        logger.info(
            "Scraped %s: %d chars across %d queries",
            repo_name,
            total_chars,
            len(queries),
        )
        results.append(RepoSearchResults(repo_name=repo_name, queries=queries))

    return results
