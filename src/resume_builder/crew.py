"""
resume_crew.py
--------------
Defines the ResumeBuilderCrew: five-agent pipeline per (resume, job) pair.
"""

from __future__ import annotations

import yaml
from pathlib import Path

from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, task

from resume_builder.settings import settings
from resume_builder.logger import get_logger
from resume_builder.models import (
    JobRequirements,
    TailoredResume,
    TailoringStrategy,
)

logger = get_logger(__name__)

_AGENTS_CONFIG_PATH = Path(__file__).parent / "config" / "agents.yaml"
_AGENTS_CONFIG_CACHE: dict | None = None


def _load_agents_config() -> dict:
    """Load and cache the full agents YAML config."""
    global _AGENTS_CONFIG_CACHE
    if _AGENTS_CONFIG_CACHE is None:
        _AGENTS_CONFIG_CACHE = yaml.safe_load(
            _AGENTS_CONFIG_PATH.read_text(encoding="utf-8")
        )
    return _AGENTS_CONFIG_CACHE


def _load_agent_config(agent_key: str) -> dict:
    """Load agent configuration from YAML, excluding the llm section."""
    cfg = _load_agents_config()
    agent_cfg = cfg.get(agent_key, {})
    return {k: v for k, v in agent_cfg.items() if k != "llm_config"}


def _create_llm(agent_key: str, default_model: str) -> LLM:
    """Create LLM instance from agent config in YAML."""
    cfg = _load_agents_config()
    agent_cfg = cfg.get(agent_key, {})
    llm_params = agent_cfg.get("llm_config", {})

    return settings.make_llm(
        model=default_model,
        temperature=llm_params.get("temperature", 0.7),
        top_p=llm_params.get("top_p", 0.9),
        max_tokens=llm_params.get("max_tokens"),
        frequency_penalty=llm_params.get("frequency_penalty", 0.0),
        presence_penalty=llm_params.get("presence_penalty", 0.0),
    )


def _get_max_iter(agent_key: str) -> int:
    """Read max_iter from agent YAML config, defaulting to 3."""
    cfg = _load_agents_config()
    return cfg.get(agent_key, {}).get("max_iter", 3)


@CrewBase
class ResumeBuilderCrew:
    """Five-agent sequential crew for a single (resume, job) pair"""

    agents_config = str(_AGENTS_CONFIG_PATH)
    tasks_config = str(Path(__file__).parent / "config" / "tasks.yaml")

    def __init__(self, session_id: str = "", job_index: int = 0) -> None:
        self._session_id = session_id
        self._job_index = job_index

    # -------------------- Agents --------------------

    @agent
    def job_analyzer(self) -> Agent:
        agent_cfg = _load_agent_config("job_analyzer")
        return Agent(
            config=agent_cfg,
            llm=_create_llm("job_analyzer", settings.analyst_model),
            verbose=settings.crewai_verbose,
            max_iter=_get_max_iter("job_analyzer"),
        )

    @agent
    def resume_strategist(self) -> Agent:
        agent_cfg = _load_agent_config("resume_strategist")
        return Agent(
            config=agent_cfg,
            llm=_create_llm("resume_strategist", settings.writer_model),
            verbose=settings.crewai_verbose,
            max_iter=_get_max_iter("resume_strategist"),
        )

    @agent
    def resume_writer(self) -> Agent:
        agent_cfg = _load_agent_config("resume_writer")
        return Agent(
            config=agent_cfg,
            llm=_create_llm("resume_writer", settings.writer_model),
            verbose=settings.crewai_verbose,
            max_iter=_get_max_iter("resume_writer"),
        )

    @agent
    def quality_reviewer(self) -> Agent:
        agent_cfg = _load_agent_config("quality_reviewer")
        return Agent(
            config=agent_cfg,
            llm=_create_llm("quality_reviewer", settings.writer_model),
            verbose=settings.crewai_verbose,
            max_iter=_get_max_iter("quality_reviewer"),
        )

    # -------------------- Tasks --------------------

    @task
    def analyze_job_task(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_job_task"],  # type: ignore[index]
            output_pydantic=JobRequirements,
        )

    @task
    def build_strategy_task(self) -> Task:
        return Task(
            config=self.tasks_config["build_strategy_task"],  # type: ignore[index]
            output_pydantic=TailoringStrategy,
            context=[self.analyze_job_task()],  # type: ignore[reportCallIssue]
        )

    @task
    def write_resume_task(self) -> Task:
        return Task(
            config=self.tasks_config["write_resume_task"],  # type: ignore[index]
            output_pydantic=TailoredResume,
            context=[
                self.analyze_job_task(),  # type: ignore[reportCallIssue]
                self.build_strategy_task(),  # type: ignore[reportCallIssue]
            ],
        )

    @task
    def review_resume_task(self) -> Task:
        return Task(
            config=self.tasks_config["review_resume_task"],  # type: ignore[index]
            output_pydantic=TailoredResume,
            context=[
                self.analyze_job_task(),  # type: ignore[reportCallIssue]
                self.build_strategy_task(),  # type: ignore[reportCallIssue]
                self.write_resume_task(),  # type: ignore[reportCallIssue]
            ],
        )

    # -------------------- Crew --------------------

    @crew
    def crew(self) -> Crew:
        logger.debug("Building crew with %d agents, process=sequential", len(self.agents))
        return Crew(
            agents=self.agents,  # pyright: ignore[reportAttributeAccessIssue]
            tasks=self.tasks,  # pyright: ignore[reportAttributeAccessIssue]
            process=Process.sequential,
            verbose=settings.crewai_verbose,
            memory=False,
        )