"""
input_parsing_crew.py
---------------------
Defines the InputParsingCrew: agents that parse program
input into a structured format.
"""

from crewai import Agent, Crew, CrewOutput, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task, llm
from crewai.agents.agent_builder.base_agent import BaseAgent
from resume_builder.logger import get_logger
from resume_builder.settings import settings
from resume_builder.models import Projects, ParsedResume

logger = get_logger(__name__)


@CrewBase
class InputParsingCrew:
    """Crew of agents to parse program inputs"""

    agents: list[BaseAgent]
    tasks: list[Task]

    @llm
    def writer_model(self) -> LLM:
        return LLM(model="gemma-4-31B-it", base_url="https://lightning.ai/api/v1/")

    @agent
    def resume_parser(self) -> Agent:
        return Agent(
            config=self.agents_config["resume_parser"],  # type: ignore[index]
            verbose=settings.crewai_verbose,
        )

    # @agent
    # def job_parser(self) -> Agent:
    #     return Agent(
    #         config=self.agents_config["job_parser"],  # type: ignore[index]
    #         verbose=settings.crewai_verbose,
    #     )
    #
    @agent
    def project_parser(self) -> Agent:
        return Agent(
            config=self.agents_config["project_parser"],  # type: ignore[index]
            verbose=settings.crewai_verbose,
        )

    @task
    def resume_parsing_task(self) -> Task:
        return Task(
            config=self.tasks_config["resume_parsing_task"],  # type: ignore[index]
            output_pydantic=ParsedResume,
        )

    # @task
    # def job_parsing_task(self) -> Task:
    #     return Task(
    #         config=self.tasks_config["job_parsing_task"]  # type: ignore[index]
    #     )
    #
    @task
    def project_parsing_task(self) -> Task:
        return Task(
            config=self.tasks_config["project_parsing_task"],  # type: ignore[index]
            output_pydantic=Projects,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the InputParsingCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=settings.crewai_verbose,
        )


if __name__ == "__main__":
    from typing import cast
    from dotenv import load_dotenv
    from pathlib import Path

    load_dotenv()

    from resume_builder.processors.project import ProjectProcessor
    from resume_builder.processors.resume import ResumeProcessor

    github_info = (
        ProjectProcessor()
        .from_github(repos=["Futtano/ai-resume-builder", "Futtano/ames-mlproject"])
        .extracted
    )
    github_info = "\n---END REPOSITORY---\n\n---BEGIN REPOSITORY\n".join(github_info)

    resume_path = (
        Path(__file__).parent.parent.parent.parent / "inputs" / "old_resume.pdf"
    )
    resume_raw_text = ResumeProcessor().from_pdf(path=resume_path).extracted
    intro_brief = ""
    output = (
        InputParsingCrew()
        .crew()
        .kickoff(
            inputs={
                "github_info": github_info,
                "resume_raw_text": resume_raw_text,
                "intro_brief": intro_brief,
            }
        )
    )

    output = cast(CrewOutput, output)

    for i, task_out in enumerate(output.tasks_output):
        print(f"Task {i}:\n{task_out.raw}\n")
