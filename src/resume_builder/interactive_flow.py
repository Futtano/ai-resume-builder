"""
interactive_flow.py
------------------
InteractiveResumeFlow — conversational resume builder with a simple REPL.

The core pattern: user's NL input + current resume state → LLM returns
updated fields as JSON → merge into working resume via model_copy(update=...).

The LLM decides whether to append, replace, or delete list items based on
the user's words — the merge code is dumb, the LLM is smart.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml
from crewai import LLM

from resume_builder.crews.job_parsing_crew.crew import JobParsingCrew
from resume_builder.crews.repo_parsing_crew.crew import RepoParsingCrew
from resume_builder.crews.resume_building_crew.crew import ResumeBuilderCrew
from resume_builder.crews.resume_parsing_crew.crew import ResumeParsingCrew
from resume_builder.logger import get_logger
from resume_builder.models import (
    ContactInfo,
    ConversationEntry,
    ImprovedResume,
    InteractiveResumeState,
    JobRequirements,
    ParsedResume,
    ProjectEntry,
    TailoredExperienceEntry,
    TailoredResume,
)
from resume_builder.settings import settings
from resume_builder.utils import render_resume

logger = get_logger(__name__)

# ── System prompt for the resume-editing LLM ──────────────────────────

_EDIT_SYSTEM_PROMPT = """\
You are a precise resume editor. You receive the current structured resume as
JSON plus a user instruction. Return a JSON object containing ONLY the
top-level fields you want to change, with their COMPLETE new values.

Critical rules:
- For NESTED OBJECTS (e.g. "contact"): return the FULL object with every
  field populated, even the ones you didn't change. The merge replaces the
  entire object.
- For LISTS (e.g. "experience", "projects", "skills"): return the COMPLETE
  list. To add items, include existing items plus new ones. To remove an
  item, omit it. To replace all items, return only the new ones.
- For SCALAR fields (e.g. "professional_summary"): return the new string.
- Fields you don't mention are left unchanged. Do NOT return fields you
  haven't modified.

The resume schema (all fields are optional except where noted):

{
  "contact": {
    "name": "string (required)",
    "email": "string",
    "phone": "string",
    "location": "string",
    "linkedin": "string",
    "github": "string",
    "portfolio": "string"
  },
  "professional_summary": "string",
  "experience": [{
    "company": "string (required)",
    "role": "string (required)",
    "start_date": "string (required)",
    "end_date": "string (required)",
    "location": "string",
    "bullets": ["string"],
    "skills_demonstrated": ["string"]
  }],
  "skills": ["string"],
  "education": [{
    "institution": "string (required)",
    "degree": "string (required)",
    "field_of_study": "string (required)",
    "start_date": "string (required)",
    "end_date": "string (required)",
    "degree_mark": "string",
    "honours": "string"
  }],
  "certifications": ["string"],
  "projects": [{
    "repo_name": "string (required)",
    "repo_url": "string (required)",
    "description": "string (required)",
    "tech_stack": ["string"],
    "architecture": "string",
    "stars": 0
  }],
  "publications": [{
    "title": "string (required)",
    "venue": "string (required)",
    "date": "string (required)",
    "publisher": "string",
    "link": "string"
  }],
  "workshops": [{
    "title": "string (required)",
    "date": "string (required)",
    "place": "string (required)"
  }],
  "awards": [{
    "title": "string (required)",
    "organization": "string (required)",
    "date": "string (required)"
  }],
  "international_experiences": [{
    "place": "string (required)",
    "date": "string (required)",
    "description": "string (required)"
  }],
  "totals_yoe": 0
}

When a project object is provided in extra context, use it as-is.
When a job posting is provided in extra context, note that it will be queued
for tailoring — you don't need to add it to the resume structure.

Return ONLY the JSON object, no other text."""


class InteractiveResumeFlow:
    """Conversational resume builder driven by a simple REPL loop."""

    def __init__(
        self,
        resume_path: Path | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self._output_dir = output_dir or settings.output_dir
        self.state = InteractiveResumeState(
            session_id=uuid.uuid4().hex[:8],
            resume_path=str(resume_path.resolve()) if resume_path else None,
        )
        llm_config_path = (
            Path(__file__).resolve().parent / "config" / "llm_interactive.yaml"
        )
        with open(llm_config_path) as fp:
            llm_config = yaml.safe_load(fp)
        self._llm = LLM(**llm_config)

    # ── Public API ────────────────────────────────────────────────────

    def run(self) -> None:
        """Start the interactive REPL loop."""
        self._initialize()
        print("\n[bold]Interactive Resume Builder[/]")
        print("Describe changes in natural language, or type a command:")
        print("  [bold]show[/]    — display current resume")
        print("  [bold]tailor[/]  — generate tailored resumes for queued jobs")
        print("  [bold]export[/]  — write .docx files")
        print("  [bold]help[/]    — show this message")
        print("  [bold]quit[/]    — save and exit")
        print()

        while True:
            try:
                raw = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nSession ended.")
                break

            if not raw:
                continue

            lowered = raw.lower()

            if lowered in ("quit", "exit"):
                self._save_state()
                tailored = len(self.state.tailored_resumes)
                print(f"Session saved. {tailored} resume(s) generated.")
                break
            elif lowered == "help":
                self._handle_help()
            elif lowered == "show":
                self._handle_show()
            elif lowered == "tailor":
                self._handle_tailor()
            elif lowered == "export":
                self._handle_export()
            else:
                self._handle_edit(raw)

    # ── Initialization ────────────────────────────────────────────────

    def _initialize(self) -> None:
        """Parse the resume PDF or create a blank resume."""
        if self.state.resume_path:
            logger.info("Parsing resume from %s", self.state.resume_path)
            try:
                result = (
                    ResumeParsingCrew()
                    .crew()
                    .kickoff(
                        inputs={
                            "intro_brief": "",
                            "resume_path": self.state.resume_path,
                        }
                    )
                )
                self.state.working_resume = result.pydantic  # type: ignore[assignment]
                logger.info("Resume loaded: %s", self.state.working_resume.contact.name)
                print(f"Loaded resume: {self.state.working_resume.contact.name}")
            except Exception as exc:
                logger.error("Failed to parse resume: %s", exc)
                print(f"Failed to parse resume: {exc}")
                print("Starting with blank resume instead.")
                self._create_blank()
        else:
            self._create_blank()
            print("Starting with blank resume.")

    def _create_blank(self) -> None:
        """Create a blank resume with placeholder contact."""
        self.state.working_resume = ParsedResume(
            contact=ContactInfo(name="Unnamed Candidate"),
        )

    # ── Edit resume ───────────────────────────────────────────────────

    def _handle_edit(self, user_input: str) -> None:
        """Core edit: LLM produces updated fields, merge into working resume."""
        wrk = self.state.working_resume
        assert wrk is not None

        # Pre-fetch external data so the LLM has it as context
        extra_context = self._prefetch(user_input)

        messages = [
            {"role": "system", "content": _EDIT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Current resume:\n{wrk.model_dump_json(indent=2)}\n\n"
                    f"{extra_context}"
                    f"Instruction: {user_input}\n\n"
                    "Return the updated fields as JSON:"
                ),
            },
        ]

        try:
            response = self._llm.call(messages)
        except Exception as exc:
            logger.error("LLM call failed: %s", exc)
            print(f"  Failed to process: {exc}")
            self._log_turn("edit_error", str(exc), user_input)
            return

        # Parse and merge — strip markdown fences if present
        try:
            update_dict = _extract_json(response)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("LLM returned invalid JSON: %s", exc)
            print(f"  Failed to parse response as JSON: {exc}")
            self._log_turn("edit_error", f"Invalid JSON: {exc}", user_input)
            return

        if not isinstance(update_dict, dict):
            print("  Unexpected response format — expected a JSON object.")
            self._log_turn("edit_error", "Response was not a dict", user_input)
            return

        if not update_dict:
            print("  No changes detected.")
            self._log_turn("edit_noop", "No fields returned", user_input)
            return

        # Merge update into full dict and re-validate so nested models
        # (AwardEntry, ExperienceEntry, etc.) are coerced from dicts.
        try:
            full_dict = wrk.model_dump()
            full_dict.update(update_dict)
            self.state.working_resume = ParsedResume.model_validate(full_dict)
        except Exception as exc:
            logger.error("Failed to merge update: %s", exc)
            print(f"  Failed to apply changes: {exc}")
            self._log_turn("edit_error", f"Merge failed: {exc}", user_input)
            return

        changed = ", ".join(update_dict.keys())
        print(f"  Updated: {changed}")
        self._log_turn("edit", f"Updated fields: {changed}", user_input)

    # ── Pre-fetch external data ───────────────────────────────────────

    def _prefetch(self, user_input: str) -> str:
        """Detect GitHub repos and job URLs in user input, fetch them.

        Returns a context string to inject into the edit prompt.
        """
        parts: list[str] = []

        # Detect GitHub repos (owner/repo format)
        repos = _extract_github_repos(user_input)
        for repo in repos:
            try:
                output = (
                    RepoParsingCrew()
                    .crew()
                    .kickoff(inputs={"source": repo, "source_type": "github_repo"})
                )
                project: ProjectEntry = output.pydantic  # type: ignore[assignment]
                parts.append(
                    f"Fetched project '{repo}':\n{project.model_dump_json(indent=2)}"
                )
                print(f"  Fetched project: {project.repo_name}")
            except Exception as exc:
                logger.error("Failed to fetch project '%s': %s", repo, exc)
                print(f"  Failed to fetch project '{repo}': {exc}")

        # Detect job URLs/files
        sources = _extract_job_sources(user_input)
        for source, source_type in sources:
            try:
                output = (
                    JobParsingCrew()
                    .crew()
                    .kickoff(inputs={"source": source, "source_type": source_type})
                )
                job_req: JobRequirements = output.pydantic  # type: ignore[assignment]
                self.state.parsed_job_postings.append(job_req)
                parts.append(f"Queued job: {job_req.job_title} at {job_req.company}")
                print(f"  Queued job: {job_req.job_title} at {job_req.company}")
            except Exception as exc:
                logger.error("Failed to parse job '%s': %s", source, exc)
                print(f"  Failed to parse job '{source}': {exc}")

        return "\n".join(parts)

    # ── Commands ──────────────────────────────────────────────────────

    def _handle_show(self) -> None:
        w = self.state.working_resume
        if not w:
            print("No resume loaded.")
            return

        lines = [
            f"\n{'=' * 60}",
            f"  {w.contact.name}",
        ]
        if w.contact.email:
            contact_line = w.contact.email
            if w.contact.phone:
                contact_line += f" | {w.contact.phone}"
            lines.append(f"  {contact_line}")

        if w.contact.linkedin:
            lines.append(f"  LinkedIn: {w.contact.linkedin}")
        if w.contact.github:
            lines.append(f"  GitHub: {w.contact.github}")
        lines.append(f"{'=' * 60}")

        if w.professional_summary:
            lines.append(f"\n  Summary: {w.professional_summary[:200]}")

        lines.append(f"\n  Skills ({len(w.skills)}): {', '.join(w.skills[:20])}")
        if len(w.skills) > 20:
            lines.append(f"    ... +{len(w.skills) - 20} more")

        lines.append(f"\n  Experience ({len(w.experience)}):")
        for e in w.experience:
            lines.append(
                f"    - {e.role} at {e.company} ({e.start_date} – {e.end_date})"
            )

        lines.append(f"\n  Education ({len(w.education)}):")
        for e in w.education:
            lines.append(f"    - {e.degree} in {e.field_of_study} — {e.institution}")

        lines.append(f"\n  Projects ({len(w.projects)}):")
        for p in w.projects:
            lines.append(f"    - {p.repo_name}: {p.description[:80]}")

        if w.publications:
            lines.append(f"\n  Publications ({len(w.publications)}):")
            for p in w.publications:
                lines.append(f"    - {p.title} ({p.venue}, {p.date})")

        if w.workshops:
            lines.append(f"\n  Workshops ({len(w.workshops)}):")
            for ws in w.workshops:
                lines.append(f"    - {ws.title} ({ws.place}, {ws.date})")

        if w.awards:
            lines.append(f"\n  Awards ({len(w.awards)}):")
            for a in w.awards:
                lines.append(f"    - {a.title} ({a.organization}, {a.date})")

        if w.certifications:
            lines.append(f"\n  Certifications: {', '.join(w.certifications)}")

        if w.international_experiences:
            lines.append(f"\n  International ({len(w.international_experiences)}):")
            for ie in w.international_experiences:
                lines.append(f"    - {ie.place} ({ie.date}): {ie.description[:80]}")

        lines.append(f"\n{'=' * 60}")

        if self.state.parsed_job_postings:
            lines.append(
                f"\n  Jobs queued for tailoring: {len(self.state.parsed_job_postings)}"
            )
            for j in self.state.parsed_job_postings:
                lines.append(f"    - {j.job_title} at {j.company}")

        if self.state.tailored_resumes:
            lines.append(f"\n  Tailored resumes: {len(self.state.tailored_resumes)}")
            for r in self.state.tailored_resumes:
                lines.append(
                    f"    - {r.company} / {r.job_title} [{r.confidence_score}%]"
                )

        lines.append("")
        print("\n".join(lines))
        self._log_turn("show", "Displayed resume summary")

    def _handle_tailor(self) -> None:
        jobs = self.state.parsed_job_postings
        if not jobs:
            print("No jobs queued. Add a job first:")
            print("  Paste a job URL or file path, e.g.:")
            print("  > https://example.com/job-posting")
            print("  > inputs/sample_job.txt")
            self._log_turn("tailor", "No jobs queued")
            return

        wrk = self.state.working_resume
        assert wrk is not None

        print(f"Tailoring for {len(jobs)} job(s)...")
        logger.info("Tailoring for %d job(s)", len(jobs))

        try:
            final_resumes = (
                ResumeBuilderCrew()
                .crew()
                .kickoff_for_each(
                    inputs=[
                        dict(
                            parsed_resume=wrk.model_dump_json(),
                            parsed_job_posting=job.model_dump_json(),
                            parsed_projects="\n".join(
                                p.model_dump_json() for p in wrk.projects
                            ),
                        )
                        for job in jobs
                    ]
                )
            )
            final_resumes = [
                r.pydantic
                for r in final_resumes  # type: ignore[assignment]
            ]
        except Exception as exc:
            logger.error("Tailoring failed: %s", exc)
            print(f"  Tailoring failed: {exc}")
            self._log_turn("tailor_error", str(exc))
            return

        improved: list[ImprovedResume] = final_resumes  # type: ignore[assignment]
        for r in improved:
            self.state.tailored_resumes.append(r.current_resume)
            print(
                f"  {r.current_resume.company} / "
                f"{r.current_resume.job_title} "
                f"[{r.current_resume.confidence_score}%]"
            )

        print(
            f"Generated {len(improved)} tailored resume(s). Use 'export' to write .docx files."
        )
        self._log_turn("tailor", f"Generated {len(improved)} resume(s)")

    def _handle_export(self) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)

        to_export = self.state.tailored_resumes
        if not to_export:
            # Export the base working resume
            base = self._prepare_base_export()
            if base is None:
                print("Nothing to export.")
                self._log_turn("export", "Nothing to export")
                return
            to_export = [base]

        exported: list[str] = []
        for resume in to_export:
            try:
                path = render_resume(resume, self._output_dir)
                if path:
                    exported.append(path)
                    print(f"  {Path(path).name}")
            except Exception as exc:
                logger.error("Failed to export %s: %s", resume.output_filename(), exc)
                print(f"  Failed: {exc}")

        print(f"Exported {len(exported)} file(s) to {self._output_dir}")
        self._log_turn("export", f"Exported {len(exported)} file(s)")

    def _handle_help(self) -> None:
        print()
        print("Describe changes in natural language, or use commands:")
        print("  show    - display current resume")
        print("  tailor  - generate tailored resumes for queued jobs")
        print("  export  - write .docx files")
        print("  help    - show this message")
        print("  quit    - save and exit")
        print()
        print("Examples:")
        print("  > My name is Jane Doe, email jane@example.com")
        print("  > Add a project futha/awesome-tool")
        print("  > Add experience: Senior Dev at ACME Corp, Jan 2022 - present")
        print("  > Remove the second experience entry")
        print("  > Add skill Rust, update summary to focus on systems programming")
        print("  > https://example.com/job-posting")
        print()

    # ── Helpers ───────────────────────────────────────────────────────

    def _log_turn(self, intent: str, summary: str, user_input: str = "") -> None:
        self.state.conversation_log.append(
            ConversationEntry(
                timestamp=datetime.now(UTC).isoformat(),
                user_input=user_input,
                intent=intent,
                result_summary=summary,
            )
        )

    def _prepare_base_export(self) -> TailoredResume | None:
        w = self.state.working_resume
        if w is None:
            return None

        return TailoredResume(
            job_title="Resume",
            company="",
            contact=w.contact,
            professional_summary=w.professional_summary,
            experience=[
                TailoredExperienceEntry(
                    company=e.company,
                    role=e.role,
                    start_date=e.start_date,
                    end_date=e.end_date,
                    location=e.location,
                    bullets=e.bullets,
                )
                for e in w.experience
            ],
            skills=w.skills,
            education=w.education,
            certifications=w.certifications,
            projects=w.projects,
            publications=w.publications,
            workshops=w.workshops,
            awards=w.awards,
            international_experiences=w.international_experiences,
            ats_keyword_coverage=[],
            missing_keywords=[],
            tailoring_notes="Base resume export from interactive builder.",
            confidence_score=0,
        )

    def _save_state(self) -> None:
        save_dir = Path("resume_sessions")
        save_dir.mkdir(exist_ok=True, parents=True)
        sid = self.state.session_id or "default"
        path = save_dir / f"{sid}.json"
        path.write_text(self.state.model_dump_json(indent=2))
        logger.debug("State saved to %s", path)


# ── Input detection helpers ────────────────────────────────────────

_GITHUB_REPO_RE = re.compile(
    r"\b(?:github\.com/)?([a-zA-Z0-9][a-zA-Z0-9._-]*/[a-zA-Z0-9._-]+)",
)


def _extract_github_repos(text: str) -> list[str]:
    """Extract owner/repo identifiers from user input."""
    # Strip URLs first to get clean owner/repo
    cleaned = text
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        cleaned = cleaned.replace(prefix, " ")
    matches = _GITHUB_REPO_RE.findall(cleaned)
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def _extract_json(response: str) -> dict:
    """Extract a JSON object from an LLM response, handling markdown fences."""
    text = response.strip()
    # Strip ```json ... ``` fences
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```")
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    result = json.loads(text)
    if not isinstance(result, dict):
        raise ValueError("Response is not a JSON object")
    return result


def _extract_job_sources(text: str) -> list[tuple[str, str]]:
    """Extract job URLs and file paths from user input. Returns (source, source_type)."""
    sources: list[tuple[str, str]] = []
    for word in text.split():
        if word.startswith(("https://", "http://")):
            sources.append((word, "url"))
        elif word.endswith(".txt") and "/" in word:
            sources.append((word, "file"))
        elif word.startswith("inputs/") and word.endswith(".txt"):
            sources.append((word, "file"))
    return sources
