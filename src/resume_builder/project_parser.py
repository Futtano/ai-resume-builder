"""
project_parser.py
-----------------
Standalone project-parsing agent — runs once per Flow execution
(if GitHub URLs are provided).

Takes raw GithubSearchTool output and produces a list of
structured ProjectEntry instances via an LLM agent with
response_format=list[ProjectEntry].
"""

from __future__ import annotations

from pathlib import Path

from crewai import Agent

from resume_builder.config import settings
from resume_builder.logger import get_logger
from resume_builder.models import ProjectEntry
from resume_builder.tools.github_scraper import RepoSearchResults

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Config path (relative to this file)
# ---------------------------------------------------------------------------
_PARSER_CONFIG_PATH = Path(__file__).parent / "config" / "github_parser_agent.yaml"


def parse_github_projects(
    search_results: list[RepoSearchResults],
) -> list[ProjectEntry]:
    """
    Parse raw GitHub search results into structured ProjectEntry models.

    Runs a single LLM agent per repo that reads the raw search output
    and extracts: description, tech stack, architecture, stars.

    Args:
        search_results: Raw results from scrape_github_repos().

    Returns:
        List of structured ProjectEntry instances.
    """
    if not search_results:
        return []

    import yaml

    logger.debug(f"Loading GitHub parser from {_PARSER_CONFIG_PATH}")
    cfg = yaml.safe_load(_PARSER_CONFIG_PATH.read_text(encoding="utf-8"))
    agent_cfg = cfg["agent"]
    task_cfg = cfg["task"]

    agent = Agent(
        role=agent_cfg["role"],
        goal=agent_cfg["goal"],
        backstory=agent_cfg["backstory"],
        llm=settings.analyst_llm,
        verbose=settings.crewai_verbose,
        max_iter=3,
        max_tokens=4096,
    )

    projects: list[ProjectEntry] = []

    for result in search_results:
        repo_name = result.repo_name
        # Build a compact prompt with all query results concatenated
        sections = []
        for query, content in result.queries.items():
            if content and len(content.strip()) > 20:
                sections.append(f"### {query}\n{content}")

        if not sections:
            logger.warning("No useful content found for %s, skipping", repo_name)
            continue

        sections_str = "\n".join(sections)
        prompt = task_cfg["description"].format(
            repo_name=repo_name, sections_str=sections_str
        )

        logger.info(
            "Parsing project info for %s (model=%s)", repo_name, settings.analyst_model
        )

        try:
            result_obj = agent.kickoff(prompt, response_format=ProjectEntry)

            if result_obj.pydantic is None:
                logger.warning("Agent returned no structured output for %s", repo_name)
                continue

            entry = result_obj.pydantic
            projects.append(entry)
            logger.info(
                "Parsed %s: %d technologies, %d stars",
                repo_name,
                len(entry.tech_stack),
                entry.stars,
            )
        except Exception as exc:
            logger.error("Failed to parse %s: %s", repo_name, exc)
            continue

    logger.info("Successfully parsed %d project(s) from GitHub", len(projects))
    return projects
