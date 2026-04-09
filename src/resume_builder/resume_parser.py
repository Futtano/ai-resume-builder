"""
resume_parser.py
----------------
Standalone resume-parsing agent — runs once per Flow execution.

Loads persona + prompt from config/resume_parser_agent.yaml,
invokes an Agent with `response_format=ParsedResume`, and returns
the structured result.  No @CrewBase magic — just a thin wrapper
so that the orchestration in flow.py stays clean.
"""

from __future__ import annotations

from pathlib import Path

from crewai import Agent

from resume_builder.config import settings
from resume_builder.logger import get_logger
from resume_builder.models import ParsedResume

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Config path (relative to this file)
# ---------------------------------------------------------------------------
_PARSER_CONFIG_PATH = Path(__file__).parent / "config" / "resume_parser_agent.yaml"


def parse_resume(
    resume_raw_text: str,
    intro_brief: str = "",
) -> ParsedResume:
    """
    Parse raw resume text into a structured ParsedResume model.

    Runs the agent exactly once.  Raises if the LLM fails to return
    structured output.

    Args:
        resume_raw_text: Full text extracted from the candidate's PDF.
        intro_brief: Optional additional candidate context.
        llm: Override the default analyst model.

    Returns:
        A fully populated ParsedResume instance.
    """
    import yaml

    logger.debug("Loading resume parser agent config")
    cfg = yaml.safe_load(_PARSER_CONFIG_PATH.read_text(encoding="utf-8"))
    agent_cfg = cfg["agent"]
    task_cfg = cfg["task"]

    logger.debug("Creating resume parser agent with model=%s", settings.analyst_model)
    agent = Agent(
        role=agent_cfg["role"],
        goal=agent_cfg["goal"],
        backstory=agent_cfg["backstory"],
        llm=settings.analyst_llm,
        verbose=settings.crewai_verbose,
        max_iter=3,
        max_tokens=4096,
    )

    prompt = task_cfg["description"].format(
        resume_raw_text=resume_raw_text,
        intro_brief=intro_brief,
    )

    logger.info("Running resume parser (model=%s)", settings.analyst_model)
    result = agent.kickoff(prompt, response_format=ParsedResume)

    if result.pydantic is None:  # pyright: ignore[reportAttributeAccessIssue]
        logger.error("Resume parser returned no structured output")
        raise RuntimeError(
            "Resume parser returned no structured output. "
            "Check CREWAI_VERBOSE=true logs for details."
        )

    name = result.pydantic.contact.name  # type: ignore[reportReturnType]
    logger.info("Resume parsing complete: %s", name)
    return result.pydantic  # type: ignore[reportReturnType]
