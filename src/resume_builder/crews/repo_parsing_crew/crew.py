"""
repo_parsing_crew/crew.py
------------------------
Parse GitHub repository information into a ProjectEntry structured Pydantic model
"""

from typing import Any
import asyncio
from pathlib import Path

from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai import Agent, Task, Crew, Process, LLM
from crewai.project import CrewBase, agent, task, crew, llm

from resume_builder.models import ProjectEntry
from resume_builder.settings import settings
from resume_builder.crews.repo_parsing_crew.tools import (
    GitHubListDirTool,
    GitHubFileReadTool,
)


@CrewBase
class RepoParsingCrew:
    """Repo Parsing Crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm_config = Path(__file__).resolve().parent / "config" / "llm.yaml"

    @llm
    def repo_parser_llm(self) -> LLM:
        import yaml

        with open(self.llm_config, "r", encoding="utf-8") as fp:
            llm_config: dict[str, Any] = yaml.safe_load(fp)
            print(llm_config)
        return LLM(**llm_config)

    @agent
    def repo_parser(self) -> Agent:
        return Agent(
            config=self.agents_config["repo_parser"],  # type: ignore[index]
            verbose=settings.crewai_verbose,
            tools=[GitHubListDirTool(), GitHubFileReadTool()],
        )

    @task
    def parse_repo(self) -> Task:
        return Task(
            config=self.tasks_config["parse_repo"],  # type: ignore[index]
            output_pydantic=ProjectEntry,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the RepoParsingCrew"""
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

    repos = ["Futtano/ai-resume-builder", "Futtano/ames-mlproject"]

    async def parse_more_projects(repos: list[str]) -> list[ProjectEntry]:
        async def parse_project(repo: str) -> ProjectEntry:
            output = (
                RepoParsingCrew()
                .crew()
                .kickoff(inputs={"source": repo, "source_type": "github_repo"})
            )
            return output.pydantic  # type: ignore

        tasks = []

        for repo in repos:
            task = asyncio.create_task(parse_project(repo=repo))
            tasks.append(task)

        parsed_projects = await asyncio.gather(*tasks)
        return parsed_projects

    parsed_projects = asyncio.run(parse_more_projects(repos=repos))
    for i, parsed_project in enumerate(parsed_projects):
        print(f"---- PARSED PROJECT {i} ----")
        print(parsed_project)
        print("-" * 24, "\n")
