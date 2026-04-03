"""
resume_crew.py
--------------
Defines the ResumeBuilderCrew: five-agent pipeline per (resume, job) pair.
"""

from __future__ import annotations

from pathlib import Path

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from resume_builder.config import settings
from resume_builder.models import (
    JobRequirements,
    ParsedResume,
    TailoredResume,
    TailoringStrategy,
)


@CrewBase
class ResumeBuilderCrew:
    """Five-agent sequential crew for a single (resume, job) pair"""

    agents_config = str(Path(__file__).parent / "config" / "agents.yaml")
    tasks_config = str(Path(__file__).parent / "config" / "tasks.yaml")

    def __init__(self, session_id: str = "", job_index: int = 0) -> None:
        super().__init__()
        self._session_id = session_id
        self._job_index = job_index
        self._session_id = session_id

    # -------------------- Agents --------------------

    @agent
    def resume_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config["resume_analyzer"],  # type: ignore[index]
            llm=settings.analyst_model,
            verbose=settings.crewai_verbose,
            max_iter=3,
            max_tokens=4096,
        )

    @agent
    def job_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config["job_analyzer"],  # type: ignore[index]
            llm=settings.analyst_model,
            verbose=settings.crewai_verbose,
            max_iter=3,
            max_tokens=2048,
        )

    @agent
    def resume_strategist(self) -> Agent:
        return Agent(
            config=self.agents_config["resume_strategist"],  # type: ignore[index]
            llm=settings.writer_model,
            verbose=settings.crewai_verbose,
            max_iter=4,
            max_tokens=2048,
        )

    @agent
    def resume_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["resume_writer"],  # type: ignore[index]
            llm=settings.writer_model,
            verbose=settings.crewai_verbose,
            max_iter=5,
            max_tokens=8192,
        )

    @agent
    def quality_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["quality_reviewer"],  # type: ignore[index]
            llm=settings.writer_model,
            verbose=settings.crewai_verbose,
            max_iter=4,
            max_tokens=8192,
        )

    # -------------------- Tasks --------------------

    @task
    def parse_resume_task(self) -> Task:
        return Task(
            config=self.tasks_config["parse_resume_task"],  # type: ignore[index]
            output_pydantic=ParsedResume,
        )

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
            context=[self.parse_resume_task, self.analyze_job_task],
        )

    @task
    def write_resume_task(self) -> Task:
        return Task(
            config=self.tasks_config["write_resume_task"],  # type: ignore[index]
            output_pydantic=TailoredResume,
            context=[
                self.parse_resume_task,
                self.analyze_job_task,
                self.build_strategy_task,
            ],
        )

    @task
    def review_resume_task(self) -> Task:
        return Task(
            config=self.tasks_config["review_resume_task"],  # type: ignore[index]
            output_pydantic=TailoredResume,
            context=[
                self.parse_resume_task,
                self.analyze_job_task,
                self.build_strategy_task,
                self.write_resume_task,
            ],
        )

    # -------------------- Crew --------------------

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # pyright: ignore[reportAttributeAccessIssue]
            tasks=self.tasks,  # pyright: ignore[reportAttributeAccessIssue]
            process=Process.sequential,
            verbose=settings.crewai_verbose,
            memory=False,
        )
