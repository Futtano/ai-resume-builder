"""
job_parsing_crew/crew.py
------------------------
Parse a job posting into a JobPosting structured Pydantic model
"""

from typing import Any
import asyncio
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai import Agent, Task, Crew, Process, LLM
from crewai.project import CrewBase, agent, task, crew, llm
from resume_builder.models import JobRequirements
from resume_builder.settings import settings
from pathlib import Path


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

        with open(self.llm_config, "r", encoding="utf-8") as fp:
            llm_config: dict[str, Any] = yaml.safe_load(fp)
            print(llm_config)
        return LLM(**llm_config)

    @agent
    def job_parser(self) -> Agent:
        return Agent(
            config=self.agents_config["job_parser"],  # type: ignore[index]
            verbose=settings.crewai_verbose,
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
    from dotenv import load_dotenv
    from pathlib import Path

    load_dotenv()

    job_files = (
        Path.home() / "hack" / "py-projects" / "resume_builder" / "inputs"
    ).glob("*.txt")

    async def parse_more_jobs(job_files):
        async def parse_job(job_posting_raw: str) -> JobRequirements:
            output = (
                JobParsingCrew()
                .crew()
                .kickoff(
                    inputs={
                        "job_posting_raw": job_posting_raw,
                    }
                )
            )
            return output.pydantic  # type: ignore

        tasks = []

        for job in job_files:
            job_posting_raw = ""
            with open(job, "r", encoding="utf-8") as fp:
                job_posting_raw = fp.read()
            # Schedule each chapter writing task
            task = asyncio.create_task(parse_job(job_posting_raw=job_posting_raw))
            tasks.append(task)

        parsed_jobs = await asyncio.gather(*tasks)
        return parsed_jobs

    parsed_jobs = asyncio.run(parse_more_jobs(job_files))
    for i, parsed_job in enumerate(parsed_jobs):
        print(f"---- PARSED JOB {i} ----")
        print(parsed_job)
        print("-" * 24, "\n")
