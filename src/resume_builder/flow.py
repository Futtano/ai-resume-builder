"""
flow.py
-------
ResumeBuilderFlow — outer orchestrator for the resume tailoring pipeline.

Pipeline steps:
  1. extract_resume   — extract text from PDF (once)
  2. parse_resume     — parse into structured ParsedResume (once, standalone agent)
  3. generate_tailored_resume — run one 4-agent crew per job posting
  4. export_documents — write all results to .docx files
"""

from pathlib import Path
from typing import Callable, cast

from crewai.flow.flow import Flow, listen, start, and_

from resume_builder.settings import settings
from resume_builder.crews.resume_building_crew.crew import ResumeBuilderCrew
from resume_builder.crews.resume_parsing_crew.crew import ResumeParsingCrew
from resume_builder.crews.job_parsing_crew.crew import JobParsingCrew
from resume_builder.crews.repo_parsing_crew.crew import RepoParsingCrew
from resume_builder.logger import get_logger
from resume_builder.models import (
    JobRequirements,
    ParsedResume,
    ProjectEntry,
    ResumeBuilderState,
    # TailoredResume, # TODO: Rewrite logic so that each step modifies a single TailoredResume state object
    ImprovedResume,
)
from resume_builder.utils import render_resume

logger = get_logger(__name__)


class ResumeBuilderFlow(Flow[ResumeBuilderState]):
    """
    Orchestrate the full resume tailoring pipeline.
    """

    def __init__(
        self,
        resume_path: Path,
        job_postings_raw: list[str],
        projects_raw: list[str] | None = None,
        intro_brief: str = "",
        output_dir: Path | None = None,
        on_progress: Callable[[str, int, int], None] | None = None,
    ) -> None:
        super().__init__()

        if not job_postings_raw:
            raise ValueError("Provide at least one job posting")

        self._intro_brief = intro_brief
        self._output_dir = output_dir or settings.output_dir
        self._on_progress = on_progress

        self.state.resume_path = resume_path
        self.state.job_postings_raw = list(job_postings_raw)
        self.state.projects_raw = list(projects_raw or [])
        self.state.intro_brief = intro_brief
        self.state.total_jobs = len(job_postings_raw)

    # -- Flow Steps --------------------------------------------------------

    @start()
    def parse_resume_step(self) -> None:
        """Step 1.a: Parse the resume ONCE into a structured ParsedResume."""
        self._emit_progress(
            "Parsing resume into structured model...", 0, self.state.total_jobs
        )
        logger.info("Parsing resume into structured model")

        parsed_resume = (
            ResumeParsingCrew()
            .crew()
            .kickoff(
                inputs={
                    "intro_brief": self.state.intro_brief,
                    "resume_path": str(self.state.resume_path),
                }
            )
        )
        parsed_resume = parsed_resume.pydantic  # type: ignore
        parsed_resume = cast(ParsedResume, parsed_resume)

        self.state.parsed_resume = parsed_resume

        name = parsed_resume.contact.name
        skills_count = len(parsed_resume.skills)
        yoe = parsed_resume.totals_yoe or "?"
        logger.info("Resume parsed: %s — %d skills, ~%s YOE", name, skills_count, yoe)
        self._emit_progress(
            f"✓ Resume parsed: {name} — {skills_count} skills, ~{yoe} YOE. "
            f"Starting generations...",
            0,
            self.state.total_jobs,
        )

    @start()
    def parse_jobs_step(self) -> None:
        """Step 1.b: Parse job postings' raw text into a list of JobRequirements models"""
        if not self.state.job_postings_raw:
            logger.error("List of job postings (self.state.job_postings_raw) is empty.")
            raise ValueError("List of job postings is empty.")
        count = len(self.state.job_postings_raw)
        self._emit_progress(
            f"Parsing {count} job posting(s)...",
            0,
            self.state.total_jobs,
        )
        logger.info("Parsing %d job posting(s)", count)

        # JobParsingCrew: list[str] -> list[JobRequirements]

        job_postings = (
            JobParsingCrew()
            .crew()
            .kickoff_for_each(
                inputs=[
                    dict(job_posting_raw=job_posting_raw)
                    for job_posting_raw in self.state.job_postings_raw
                ]
            )
        )
        job_postings = [posting.pydantic for posting in job_postings]  # type: ignore
        job_postings = cast(list[JobRequirements], job_postings)

        self.state.parsed_job_postings = job_postings

        self._emit_progress(
            f"✓ {len(job_postings)} job post(s) parsed.",
            0,
            self.state.total_jobs,
        )
        logger.info("Parsed %d job posting(s)", len(job_postings))

    @start()
    def parse_projects_step(self) -> None:
        """Step 1.c: Parse GitHub repos if raw Markdown data provided."""
        if not self.state.projects_raw:
            logger.debug("No GitHub projects provided, skipping project parsing")
            return

        count = len(self.state.projects_raw)
        self._emit_progress(
            f"Parsing {count} GitHub project(s)...",
            0,
            self.state.total_jobs,
        )
        logger.info("Parsing %d GitHub project(s)", count)

        # LLM parsing → structured ProjectEntry

        projects = (
            RepoParsingCrew()
            .crew()
            .kickoff_for_each(
                inputs=[
                    dict(project_raw=project_raw)
                    for project_raw in self.state.projects_raw
                ]
            )
        )
        projects = [project.pydantic for project in projects]  # type: ignore
        projects = cast(list[ProjectEntry], projects)

        self.state.parsed_projects = projects

        self._emit_progress(
            f"✓ {len(projects)} project(s) parsed from GitHub. Starting generations...",
            0,
            self.state.total_jobs,
        )
        logger.info("Parsed %d GitHub project(s)", len(projects))

    @listen(and_(parse_resume_step, parse_jobs_step, parse_projects_step))
    def generate_tailored_resume(self) -> None:
        """Step 2: Run one 3-agent crew per job posting."""
        logger.info(
            "Starting tailored resume generation for %d job(s)", self.state.total_jobs
        )
        final_resumes = (
            ResumeBuilderCrew()
            .crew()
            .kickoff_for_each(
                inputs=[
                    dict(
                        parsed_resume=self.state.parsed_resume.model_dump_json(),  # type: ignore
                        parsed_job_posting=job_posting.model_dump_json(),
                        parsed_projects="\n".join(
                            [
                                project.model_dump_json()
                                for project in self.state.parsed_projects
                            ]
                        ),
                    )
                    for job_posting in self.state.parsed_job_postings
                ]
            )
        )
        final_resumes = [resume.pydantic for resume in final_resumes]  # type: ignore
        final_resumes = cast(list[ImprovedResume], final_resumes)
        self.state.tailored_resumes = [
            resume.current_resume for resume in final_resumes
        ]

    @listen(generate_tailored_resume)
    def export_documents(self) -> None:
        """Step 4: Generate .docx files"""
        if not self.state.tailored_resumes:
            logger.warning("No resumes to export (all jobs may have failed)")
            self._emit_progress(
                "No resumes to export (all jobs may have failed).",
                0,
                self.state.total_jobs,
            )
            return

        logger.info("Generating %d resume(s)", len(self.state.tailored_resumes))
        exported: list[Path] = []

        for resume in self.state.tailored_resumes:
            try:
                docx_path = render_resume(resume, self._output_dir)
                if docx_path:
                    exported.append(Path(docx_path))
                    logger.debug("Exported: %s", docx_path)
            except Exception as exc:
                err = f"Failed to generate {resume.output_filename()}: {exc}"
                logger.error(err)
                self.state.errors.append(err)

        logger.info("%d resume(s) exported to %s", len(exported), self._output_dir)
        self._emit_progress(
            f"Done! {len(exported)} resume(s) written to {self._output_dir}",
            self.state.total_jobs,
            self.state.total_jobs,
        )

    # -- Helpers -----------------------------------------------------------

    # def _run_crew_for_job(self, job_posting_raw: str, job_index: int) -> TailoredResume:
    #     """Run one 4-agent crew execution for a single job posting."""
    #     parsed = self.state.parsed_resume
    #     if parsed is None:
    #         raise RuntimeError(
    #             "state.parsed_resume is None. The parse_resume_step flow step "
    #             "must complete before generate_tailored_resume."
    #         )
    #
    #     logger.debug("Creating crew for job %d", job_index)
    #     crew_instance = ResumeBuilderCrew(
    #         session_id="",  # pyright: ignore[reportCallIssue]
    #         job_index=job_index,  # pyright: ignore[reportCallIssue]
    #     )
    #
    #     inputs: dict = {
    #         "parsed_resume_json": parsed.model_dump_json(indent=2),
    #         "job_posting_raw": job_posting_raw,
    #         "projects_json": (
    #             json.dumps(
    #                 [p.model_dump() for p in self.state.parsed_projects],
    #                 indent=2,
    #             )
    #             if self.state.parsed_projects
    #             else "[]"
    #         ),
    #     }
    #
    #     logger.debug("Kicking off crew for job %d", job_index)
    #     result: CrewOutput | CrewStreamingOutput = crew_instance.crew().kickoff(
    #         inputs=inputs
    #     )
    #     if result.pydantic is None:  # pyright: ignore[reportAttributeAccessIssue]
    #         raise RuntimeError(
    #             "Crew returned no structured output. "
    #             "Check CREWAI_VERBOSE=true logs for quality reviewer task."
    #         )
    #     return result.pydantic  # type: ignore[reportReturnType]
    #
    def _emit_progress(self, message: str, completed: int, total: int) -> None:
        if self._on_progress:
            self._on_progress(message, completed, total)


def plot():
    flow = ResumeBuilderFlow(
        resume_path=Path("inputs/old_resume.pdf"),
        job_postings_raw=["Demo"],
    )
    flow.plot()
