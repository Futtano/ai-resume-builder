"""
project_parser.py
-----------------
Standalone project-parsing agent — runs once per Flow execution
(if GitHub URLs are provided).

Takes raw Markdown from ProjectProcessor and produces a list of
structured ProjectEntry instances via an LLM agent.
"""

from __future__ import annotations
from pprint import pprint

from pathlib import Path

from crewai import Agent

from resume_builder.config import settings
from resume_builder.logger import get_logger
from resume_builder.models import ProjectEntry

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Config path (relative to this file)
# ---------------------------------------------------------------------------
_PARSER_CONFIG_PATH = Path(__file__).parent / "config" / "project_parser_agent.yaml"


def parse_projects(
    markdown_results: list[str],
) -> list[ProjectEntry]:
    """
    Parse formatted GitHub Markdown strings into structured ProjectEntry models.

    Runs a single LLM agent per repo that reads the Markdown document
    and extracts: description, tech stack, architecture, stars.

    Args:
        markdown_results: List of Markdown strings from ProjectProcessor.

    Returns:
        List of structured ProjectEntry instances.
    """
    if not markdown_results:
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
    )

    projects: list[ProjectEntry] = []

    for content in markdown_results:
        # Extract repo name from the first line (expecting "# Repository: owner/repo")
        repo_name = "Unknown"
        first_line = content.splitlines()[0]
        if first_line.startswith("# Repository: "):
            repo_name = first_line.replace("# Repository: ", "").strip()

        prompt = task_cfg["description"].format(
            repo_name=repo_name,
            sections_str=content,
            project_entry_schema=ProjectEntry.model_json_schema(),
        )

        logger.info(
            "Parsing project info for %s (model=%s)", repo_name, settings.analyst_model
        )

        try:
            result_obj = agent.kickoff(prompt, response_format=ProjectEntry)  # type: ignore

            if result_obj.pydantic is None:  # type: ignore
                logger.warning("Agent returned no structured output for %s", repo_name)
                continue

            entry: ProjectEntry = result_obj.pydantic  # type: ignore
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


if __name__ == "__main__":
    from resume_builder.processors.project import ProjectProcessor

    processor = ProjectProcessor().from_github(["Futtano/ai-resume-builder"])
    output = parse_projects(markdown_results=processor.extracted)
    pprint(output)
