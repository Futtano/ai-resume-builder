"""
repo_building_crew/crew.py
------------------------
Builds a TailoredResume model from the old resume of the candidate,
a job posting and a (optional) list of projects
"""

from typing import Any
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai import Agent, Task, Crew, Process, LLM
from crewai.project import CrewBase, agent, task, crew, llm
from resume_builder.settings import settings
from pathlib import Path

from resume_builder.logger import get_logger
from resume_builder.models import (
    ParsedResume,
    TailoredResume,
    ImprovedResume,
    TailoringStrategy,
)

logger = get_logger(__name__)


@CrewBase
class ResumeBuilderCrew:
    """ResumeBuilderCrew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm_config = Path(__file__).resolve().parent / "config" / "llm.yaml"

    @llm
    def resume_strategist_llm(self) -> LLM:
        import yaml

        with open(self.llm_config, "r", encoding="utf-8") as fp:
            llm_config: dict[str, Any] = yaml.safe_load(fp)["resume_strategist_llm"]
            print(llm_config)
        return LLM(**llm_config)

    @llm
    def resume_writer_llm(self) -> LLM:
        import yaml

        with open(self.llm_config, "r", encoding="utf-8") as fp:
            llm_config: dict[str, Any] = yaml.safe_load(fp)["resume_writer_llm"]
            print(llm_config)
        return LLM(**llm_config)

    @llm
    def quality_reviewer_llm(self) -> LLM:
        import yaml

        with open(self.llm_config, "r", encoding="utf-8") as fp:
            llm_config: dict[str, Any] = yaml.safe_load(fp)["quality_reviewer_llm"]
            print(llm_config)
        return LLM(**llm_config)

    @agent
    def resume_strategist(self) -> Agent:
        return Agent(
            config=self.agents_config["resume_strategist"],  # type: ignore[index]
            verbose=settings.crewai_verbose,
        )

    @agent
    def resume_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["resume_writer"],  # type: ignore[index]
            verbose=settings.crewai_verbose,
        )

    @agent
    def quality_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["quality_reviewer"],  # type: ignore[index]
            verbose=settings.crewai_verbose,
        )

    # -------------------- Tasks --------------------

    @task
    def resume_strategist_task(self) -> Task:
        return Task(
            config=self.tasks_config["resume_strategist_task"],  # type: ignore[index]
            output_pydantic=TailoringStrategy,
        )

    @task
    def resume_writer_task(self) -> Task:
        return Task(
            config=self.tasks_config["resume_writer_task"],  # type: ignore[index]
            output_pydantic=TailoredResume,
        )

    # TODO: Maybe an improvement loop writer->reviewer->writer etc. may be cool

    @task
    def quality_reviewer_task(self) -> Task:
        return Task(
            config=self.tasks_config["quality_reviewer_task"],  # type: ignore[index]
            output_pydantic=ImprovedResume,
        )

    # -------------------- Crew --------------------

    @crew
    def crew(self) -> Crew:
        logger.debug(
            "Building crew with %d agents, process=sequential", len(self.agents)
        )
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
    from resume_builder.models import ProjectEntry, JobRequirements, ImprovedResume
    from resume_builder.processors.resume import ResumeProcessor
    from resume_builder.processors.project import ProjectProcessor
    from resume_builder.processors.job import JobProcessor
    from resume_builder.crews.repo_parsing_crew.crew import RepoParsingCrew
    from resume_builder.crews.resume_parsing_crew.crew import ResumeParsingCrew
    from resume_builder.crews.job_parsing_crew.crew import JobParsingCrew
    from resume_builder.processors.formatter import ResumeFormatter

    load_dotenv()

    projects_raw = (
        ProjectProcessor()
        .from_github(["Futtano/ai-resume-builder", "Futtano/ames-mlproject"])
        .extracted
    )

    projects = (
        RepoParsingCrew()
        .crew()
        .kickoff_for_each(
            inputs=[dict(project_raw=project_raw) for project_raw in projects_raw]
        )
    )
    projects = [project.pydantic for project in projects]  # type: ignore
    projects = cast(list[ProjectEntry], projects)

    resume_path = Path("inputs/old_resume.pdf")
    resume_raw_text = ResumeProcessor().from_pdf(resume_path).extracted

    output = (
        ResumeParsingCrew()
        .crew()
        .kickoff(inputs={"intro_brief": "", "resume_raw_text": resume_raw_text})
    )
    parsed_resume = output.pydantic  # type: ignore
    parsed_resume = cast(ParsedResume, parsed_resume)

    job_postings_raw = JobProcessor().from_directory(Path("inputs/")).extracted

    job_postings = (
        JobParsingCrew()
        .crew()
        .kickoff_for_each(
            inputs=[
                dict(job_posting_raw=job_posting_raw)
                for job_posting_raw in job_postings_raw
            ]
        )
    )
    job_postings = [posting.pydantic for posting in job_postings]  # type: ignore
    job_postings = cast(list[JobRequirements], job_postings)

    final_resumes = (
        ResumeBuilderCrew()
        .crew()
        .kickoff_for_each(
            inputs=[
                dict(
                    parsed_resume=parsed_resume.model_dump_json(),
                    parsed_job_posting=job_posting.model_dump_json(),
                    parsed_projects="\n".join(
                        [project.model_dump_json() for project in projects]
                    ),
                )
                for job_posting in job_postings
            ]
        )
    )
    final_resumes = [resume.pydantic for resume in final_resumes]  # type: ignore
    final_resumes = cast(list[ImprovedResume], final_resumes)

    for i, resume in enumerate(final_resumes):
        print("-" * 10, f" FINAL RESUME {i + 1} ", "-" * 10)
        print(resume, "\n")

    formatter = ResumeFormatter()
    exported: list[Path] = []

    resumes_to_export = [resume.current_resume for resume in final_resumes]

    for resume in resumes_to_export:
        path = formatter.generate(resume, output_dir=Path("outputs/"))
        exported.append(path)

    print("%d resume(s) exported to %s", len(exported), Path("outputs/"))
    print(
        f"Done! {len(exported)} resume(s) written to {Path('outputs/')}",
    )
