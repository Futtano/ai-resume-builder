"""
resume_parsing_crew/crew.py
------------------------
Parse a resume PDF into a ParsedResume structured Pydantic model.
"""

import argparse
from pathlib import Path
from typing import Any

from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai import Agent, Task, Crew, Process, LLM
from crewai.project import CrewBase, agent, task, crew, llm
from crewai_tools import FileReadTool
from resume_builder.crews.resume_parsing_crew.tools import ExtractResumeContentTool
from resume_builder.models import ParsedResume
from resume_builder.settings import settings


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
            tools=[ExtractResumeContentTool(), FileReadTool()],
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


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Smoke test the resume parsing crew against a local PDF resume."
    )
    parser.add_argument("resume_pdf", type=Path, help="Path to the resume PDF file")
    parser.add_argument(
        "--intro",
        default="",
        help="Optional short professional introduction to feed into the parser.",
    )
    args = parser.parse_args()

    resume_path = args.resume_pdf.resolve()

    output = (
        ResumeParsingCrew()
        .crew()
        .kickoff(
            inputs={
                "intro_brief": args.intro,
                "resume_pdf_path": str(resume_path),
            }
        )
    )

    print("-" * 8, "ParsedResume", "-" * 8)
    print(output.pydantic)  # type: ignore


if __name__ == "__main__":
    main()
