"""
job_parsing_crew/crew.py
------------------------
Parse a job posting into a JobPosting structured Pydantic model
"""

import asyncio
from pathlib import Path
from typing import Any

from crewai import LLM, Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, llm, task
from crewai_tools import FileReadTool

from resume_builder.crews.job_parsing_crew.tools import JobURLScrapeTool
from resume_builder.models import JobRequirements
from resume_builder.settings import settings


@CrewBase
class JobParsingCrew:
    """Job Parsing Crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm_config = Path(__file__).resolve().parent / "config" / "llm.yaml"

    @llm
    def job_parser_llm(self) -> LLM:
        import yaml

        with open(self.llm_config, encoding="utf-8") as fp:
            llm_config: dict[str, Any] = yaml.safe_load(fp)
        return LLM(**llm_config)

    @agent
    def job_parser(self) -> Agent:
        return Agent(
            config=self.agents_config["job_parser"],  # type: ignore[index]
            verbose=settings.crewai_verbose,
            tools=[FileReadTool(), JobURLScrapeTool()],
        )

    @task
    def parse_job(self) -> Task:
        return Task(
            config=self.tasks_config["parse_job"],  # type: ignore[index]
            output_pydantic=JobRequirements,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the JobParsingCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=settings.crewai_verbose,
        )


if __name__ == "__main__":
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv()

    job_files = (
        Path.home() / "hack" / "py-projects" / "resume_builder" / "inputs"
    ).glob("*.txt")

    async def parse_more_jobs(job_files):
        async def parse_job(source: str, source_type: str) -> JobRequirements:
            output = (
                JobParsingCrew()
                .crew()
                .kickoff(
                    inputs={
                        "source": source,
                        "source_type": source_type,
                    }
                )
            )
            return output.pydantic  # type: ignore

        tasks = []

        for job in job_files:
            task = asyncio.create_task(parse_job(source=str(job), source_type="file"))
            tasks.append(task)

        parsed_jobs = await asyncio.gather(*tasks)
        return parsed_jobs

    parsed_jobs = asyncio.run(parse_more_jobs(job_files))
    for i, parsed_job in enumerate(parsed_jobs):
        print(f"---- PARSED JOB {i} ----")
        print(parsed_job)
        print("-" * 24, "\n")
