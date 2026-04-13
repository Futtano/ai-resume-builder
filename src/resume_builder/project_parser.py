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

from dataclasses import asdict

from crewai import Agent

from resume_builder.config import settings
from resume_builder.logger import get_logger
from resume_builder.models import ProjectEntry
from resume_builder.tools.github_scraper import RepoSearchResults

logger = get_logger(__name__)


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

    agent = Agent(
        role="Technical Project Analyst",
        goal="Analyze GitHub repository search results and extract structured project information for a resume.",
        backstory=(
            "You are a senior technical recruiter and engineering manager who has "
            "reviewed thousands of GitHub portfolios. You can quickly identify the "
            "most impressive aspects of a project: its purpose, the technology stack, "
            "how the system is architected, and what makes it stand out. You never "
            "invent information — if something isn't in the search results, you leave "
            "it out rather than fabricating details."
        ),
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

        prompt = (
            f"Analyze the following search results for the GitHub repository "
            f"{repo_name} and extract structured project information.\n\n"
            f"Return ONLY a JSON object with these fields:\n"
            f"- repo_name: the repository name (e.g. 'owner/repo')\n"
            f"- repo_url: the full URL to the repository\n"
            f"- description: a short but comprehensive description of what the project does (2-3 sentences)\n"
            f"- tech_stack: list of technologies, languages, and frameworks used\n"
            f"- architecture: high-level explanation of how the project works — information flow, "
            f"how components interact, system design (3-5 sentences)\n"
            f"- stars: the GitHub stars count (integer, 0 if not found)\n\n"
            f"Do NOT invent information. If a field cannot be determined from the "
            f"search results, use an empty string for description/architecture, "
            f"an empty list for tech_stack, and 0 for stars.\n\n"
            f"--- Search Results for {repo_name} ---\n\n"
            f"{chr(10).join(sections)}"
        )

        logger.info("Parsing project info for %s (model=%s)", repo_name, settings.analyst_model)

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
