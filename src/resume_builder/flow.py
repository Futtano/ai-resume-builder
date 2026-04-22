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

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from crewai.crews.crew_output import CrewOutput
from crewai.flow.flow import Flow, listen, start
from crewai.types.streaming import CrewStreamingOutput

from resume_builder.config import settings
from resume_builder.crew import ResumeBuilderCrew
from resume_builder.logger import get_logger
from resume_builder.models import ResumeBuilderState, TailoredResume
from resume_builder.project_parser import parse_projects
from resume_builder.resume_parser import parse_resume
from resume_builder.processors.formatter import ResumeFormatter

logger = get_logger(__name__)


class ResumeBuilderFlow(Flow[ResumeBuilderState]):
    """
    Orchestrate the full resume tailoring pipeline.
    """

    def __init__(
        self,
        resume_raw_text: str,
        job_postings_raw: list[str],
        projects_raw: Optional[list[str]] = None,
        intro_brief: str = "",
        output_dir: Optional[Path] = None,
        on_progress: Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        super().__init__()

        if not resume_raw_text.strip():
            raise ValueError("resume_raw_text cannot be empty")
        if not job_postings_raw:
            raise ValueError("Provide at least one job posting")

        self._intro_brief = intro_brief
        self._output_dir = output_dir or settings.output_dir
        self._on_progress = on_progress

        self.state.resume_raw_text = resume_raw_text
        self.state.job_postings_raw = list(job_postings_raw)
        self.state.projects_raw = list(projects_raw or [])
        self.state.intro_brief = intro_brief
        self.state.total_jobs = len(job_postings_raw)

    # -- Flow Steps --------------------------------------------------------

    @start()
    def parse_resume_step(self) -> None:
        """Step 1: Parse the resume ONCE into a structured ParsedResume."""
        self._emit_progress(
            "Parsing resume into structured model...", 0, self.state.total_jobs
        )
        logger.info("Parsing resume into structured model")

        parsed = parse_resume(
            resume_raw_text=self.state.resume_raw_text,
            intro_brief=self.state.intro_brief,
        )
        self.state.parsed_resume = parsed

        name = parsed.contact.name
        skills_count = len(parsed.skills)
        yoe = parsed.totals_yoe or "?"
        logger.info("Resume parsed: %s — %d skills, ~%s YOE", name, skills_count, yoe)
        self._emit_progress(
            f"✓ Resume parsed: {name} — {skills_count} skills, ~{yoe} YOE. "
            f"Starting generations...",
            0,
            self.state.total_jobs,
        )

    @listen(parse_resume_step)
    def parse_github_projects_step(self) -> None:
        """Step 2: Parse GitHub repos if raw Markdown data provided."""
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
        projects = parse_projects(self.state.projects_raw)
        self.state.parsed_projects = projects

        self._emit_progress(
            f"✓ {len(projects)} project(s) parsed from GitHub. Starting generations...",
            0,
            self.state.total_jobs,
        )
        logger.info("Parsed %d GitHub project(s)", len(projects))

    @listen(parse_github_projects_step)
    def generate_tailored_resume(self) -> None:
        """Step 3: Run one 4-agent crew per job posting."""
        logger.info(
            "Starting tailored resume generation for %d job(s)", self.state.total_jobs
        )
        for (
            index,
            job_posting_raw,
        ) in enumerate(self.state.job_postings_raw):
            label = f"job {index + 1}/{self.state.total_jobs}"
            self._emit_progress(f"Processing {label}...", index, self.state.total_jobs)
            logger.info("Processing %s", label)

            try:
                resume = self._run_crew_for_job(job_posting_raw, index)
                self.state.tailored_resumes.append(resume)
                self.state.completed_jobs += 1

                logger.info(
                    "✓ %s complete — %s at %s (confidence: %d%%)",
                    label,
                    resume.job_title,
                    resume.company,
                    resume.confidence_score,
                )
                self._emit_progress(
                    f"✓ {label} complete -- {resume.job_title} at {resume.company} "
                    f"(confidence: {resume.confidence_score}%)",
                    self.state.completed_jobs,
                    self.state.total_jobs,
                )
            except Exception as exc:
                msg = f"✗ {label} failed: {exc}"
                logger.error("✗ %s failed", label, exc_info=True)
                self.state.errors.append(msg)
                self._emit_progress(
                    msg, self.state.completed_jobs, self.state.total_jobs
                )

    @listen(generate_tailored_resume)
    def export_documents(self) -> None:
        """Step 4: Convert all TailoredResume objects to .docx files."""
        if not self.state.tailored_resumes:
            logger.warning("No resumes to export (all jobs may have failed)")
            self._emit_progress(
                "No resumes to export (all jobs may have failed).",
                0,
                self.state.total_jobs,
            )
            return

        logger.info("Exporting %d resume(s) to .docx", len(self.state.tailored_resumes))
        formatter = ResumeFormatter()
        exported: list[Path] = []

        for resume in self.state.tailored_resumes:
            try:
                path = formatter.generate(resume, output_dir=self._output_dir)
                exported.append(path)
                logger.debug("Exported: %s", path)
            except Exception as exc:
                err = f"Failed to export {resume.output_filename()}: {exc}"
                logger.error("Export failed for %s: %s", resume.output_filename(), exc)
                self.state.errors.append(err)

        logger.info("%d resume(s) exported to %s", len(exported), self._output_dir)
        self._emit_progress(
            f"Done! {len(exported)} resume(s) written to {self._output_dir}",
            self.state.total_jobs,
            self.state.total_jobs,
        )

    # -- Helpers -----------------------------------------------------------

    def _run_crew_for_job(self, job_posting_raw: str, job_index: int) -> TailoredResume:
        """Run one 4-agent crew execution for a single job posting."""
        parsed = self.state.parsed_resume
        if parsed is None:
            raise RuntimeError(
                "state.parsed_resume is None. The parse_resume_step flow step "
                "must complete before generate_tailored_resume."
            )

        logger.debug("Creating crew for job %d", job_index)
        crew_instance = ResumeBuilderCrew(
            session_id="",  # pyright: ignore[reportCallIssue]
            job_index=job_index,  # pyright: ignore[reportCallIssue]
        )

        inputs: dict = {
            "parsed_resume_json": parsed.model_dump_json(indent=2),
            "job_posting_raw": job_posting_raw,
            "projects_json": (
                json.dumps(
                    [p.model_dump() for p in self.state.parsed_projects],
                    indent=2,
                )
                if self.state.parsed_projects
                else "[]"
            ),
        }

        logger.debug("Kicking off crew for job %d", job_index)
        result: CrewOutput | CrewStreamingOutput = crew_instance.crew().kickoff(
            inputs=inputs
        )
        if result.pydantic is None:  # pyright: ignore[reportAttributeAccessIssue]
            raise RuntimeError(
                "Crew returned no structured output. "
                "Check CREWAI_VERBOSE=true logs for quality reviewer task."
            )
        return result.pydantic  # type: ignore[reportReturnType]

    def _emit_progress(self, message: str, completed: int, total: int) -> None:
        if self._on_progress:
            self._on_progress(message, completed, total)
