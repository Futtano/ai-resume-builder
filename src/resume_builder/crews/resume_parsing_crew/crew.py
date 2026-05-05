"""
resume_parsing_crew/crew.py
------------------------
Parse extracted text from a resume into a ParsedResume structured Pydantic model
"""

from typing import Any
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai import Agent, Task, Crew, Process, LLM
from crewai.project import CrewBase, agent, task, crew, llm
from resume_builder.models import ParsedResume
from resume_builder.settings import settings
from pathlib import Path


@CrewBase
class ResumeParsingCrew:
    """Resume Parsing Crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm_config = Path(__file__).resolve().parent / "config" / "llm.yaml"

    @llm
    def resume_parser_llm(self) -> LLM:
        import yaml

        with open(self.llm_config, "r", encoding="utf-8") as fp:
            llm_config: dict[str, Any] = yaml.safe_load(fp)
            print(llm_config)
        return LLM(**llm_config)

    @agent
    def resume_parser(self) -> Agent:
        return Agent(
            config=self.agents_config["resume_parser"],  # type: ignore[index]
            verbose=settings.crewai_verbose,
        )

    @task
    def parse_resume(self) -> Task:
        return Task(
            config=self.tasks_config["parse_resume"],  # type: ignore[index]
            output_pydantic=ParsedResume,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the ResumeParsingCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=settings.crewai_verbose,
        )


if __name__ == "__main__":
    from dotenv import load_dotenv
    from pathlib import Path
    from resume_builder.processors.resume import ResumeProcessor

    load_dotenv()

    resume_path = Path("inputs/old_resume.pdf")
    resume_raw_text = ResumeProcessor().from_pdf(resume_path).extracted

    output = (
        ResumeParsingCrew()
        .crew()
        .kickoff(inputs={"intro_brief": "", "resume_raw_text": resume_raw_text})
    )

    print("-" * 8, "ParsedResume", "-" * 8)
    print(output.pydantic)  # type: ignore
