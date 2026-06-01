"""InteractiveSessionService — all business logic for the interactive API.

Extracted from InteractiveResumeFlow so the REPL and the API share the same
LLM edit pattern, crew invocations, and session management.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from crewai import LLM

from resume_builder.api.core.workers import run_in_executor
from resume_builder.api.errors import (
    AppError,
    invalid_instruction,
    llm_failure,
    no_jobs_queued,
    no_resume_loaded,
    session_not_found,
)
from resume_builder.api.stores.base import SessionStore
from resume_builder.crews.job_parsing_crew.crew import JobParsingCrew
from resume_builder.crews.repo_parsing_crew.crew import RepoParsingCrew
from resume_builder.crews.resume_building_crew.crew import ResumeBuilderCrew
from resume_builder.crews.resume_parsing_crew.crew import ResumeParsingCrew
from resume_builder.interactive_flow import (
    _EDIT_SYSTEM_PROMPT,
    _extract_github_repos,
    _extract_job_sources,
    _extract_json,
)
from resume_builder.logger import get_logger
from resume_builder.models import (
    ContactInfo,
    ConversationEntry,
    ImprovedResume,
    InteractiveResumeState,
    JobRequirements,
    ParsedResume,
    ProjectEntry,
)
from resume_builder.utils import render_resume

logger = get_logger(__name__)

# ── In-memory task tracking ──

_TASK_STORE: dict[str, dict[str, Any]] = {}


def _set_task(task_id: str, **fields: Any) -> None:
    fields.setdefault("status", "queued")
    _TASK_STORE[task_id] = fields


def _get_task(task_id: str) -> dict[str, Any] | None:
    return _TASK_STORE.get(task_id)


class InteractiveSessionService:
    """Business logic for interactive resume tailoring sessions."""

    def __init__(self, store: SessionStore) -> None:
        self._store = store
        # Load LLM config once (same config as the REPL)
        llm_config_path = (
            Path(__file__).resolve().parent.parent.parent
            / "config"
            / "llm_interactive.yaml"
        )
        with open(llm_config_path) as fp:
            llm_config = yaml.safe_load(fp)
        self._llm = LLM(**llm_config)

    # ── Session CRUD ────────────────────────────────────────────────

    async def create_session(self, user_id: str) -> InteractiveResumeState:
        """Create a new blank session."""
        state = InteractiveResumeState(
            session_id=uuid.uuid4().hex,
            working_resume=ParsedResume(
                contact=ContactInfo(name="Unnamed Candidate"),
                experience=[],
                skills=[],
                education=[],
            ),
        )
        await self._store.save(user_id, state.session_id, state)
        logger.info("Created session %s for user %s", state.session_id, user_id)
        return state

    async def get_session(
        self, user_id: str, session_id: str
    ) -> InteractiveResumeState:
        """Get a session by ID. Raises AppError if not found."""
        state = await self._store.get(user_id, session_id)
        if state is None:
            raise session_not_found(session_id)
        return state

    async def list_sessions(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> tuple[list, int]:
        """List sessions for a user. Returns (items, total)."""
        return await self._store.list(user_id, limit, offset)

    async def delete_session(self, user_id: str, session_id: str) -> bool:
        """Delete a session and its files."""
        return await self._store.delete(user_id, session_id)

    # ── Resume upload / parse ───────────────────────────────────────

    async def upload_resume(
        self, user_id: str, session_id: str, content: bytes, filename: str
    ) -> Path:
        """Save an uploaded resume PDF and update session state."""
        state = await self.get_session(user_id, session_id)
        dest_dir = Path("uploads") / user_id / "files" / session_id

        def _write() -> Path:
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / "resume.pdf"
            dest.write_bytes(content)
            return dest

        path = await run_in_executor(_write)
        state.resume_path = str(path.resolve())
        await self._store.save(user_id, session_id, state)
        return path

    async def parse_resume(self, user_id: str, session_id: str) -> str:
        """Enqueue resume parsing in the thread pool. Returns task_id."""
        state = await self.get_session(user_id, session_id)
        if not state.resume_path:
            raise AppError(400, "NO_RESUME_FILE", "Upload a resume PDF first")

        task_id = uuid.uuid4().hex
        _set_task(task_id, status="queued")

        async def _run() -> None:
            _set_task(task_id, status="running")
            try:
                output = await run_in_executor(
                    lambda: (
                        ResumeParsingCrew()
                        .crew()
                        .kickoff(
                            inputs={
                                "intro_brief": "",
                                "resume_path": state.resume_path,
                            }
                        )
                    )
                )
                parsed: ParsedResume = output.pydantic
                state.working_resume = parsed
                await self._store.save(user_id, session_id, state)
                _set_task(task_id, status="completed", result=parsed)
                logger.info(
                    "Parsed resume for session %s: %s (%d skills)",
                    session_id,
                    parsed.contact.name,
                    len(parsed.skills),
                )
            except Exception as exc:
                logger.error("Resume parsing failed: %s", exc)
                _set_task(
                    task_id,
                    status="failed",
                    error={"detail": str(exc), "error_code": "CREW_FAILURE"},
                )

        # Fire and forget — task writes to _TASK_STORE, client polls
        import asyncio

        asyncio.create_task(_run())
        return task_id

    # ── Natural-language edit (the core pattern) ────────────────────

    async def apply_edit(
        self, user_id: str, session_id: str, instruction: str
    ) -> dict[str, Any]:
        """Apply a natural-language edit to the working resume.

        Runs the full _handle_edit pipeline: prefetch → LLM call → merge → persist.
        Returns {updated_fields, working_resume, conversation_entry}.
        """
        state = await self.get_session(user_id, session_id)
        wrk = state.working_resume
        if wrk is None:
            raise no_resume_loaded()

        # 1. Pre-fetch external data
        extra_context = await run_in_executor(self._prefetch, state, instruction)

        # 2. Build prompt and call LLM
        messages = [
            {"role": "system", "content": _EDIT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Current resume:\n{wrk.model_dump_json(indent=2)}\n\n"
                    f"{extra_context}"
                    f"Instruction: {instruction}\n\n"
                    "Return the updated fields as JSON:"
                ),
            },
        ]

        try:
            response = await run_in_executor(self._llm.call, messages)
        except Exception as exc:
            logger.error("LLM call failed: %s", exc)
            self._log_turn(state, "edit_error", str(exc), instruction)
            raise llm_failure(str(exc)) from exc

        # 3. Parse JSON response
        try:
            update_dict = _extract_json(response)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("LLM returned invalid JSON: %s", exc)
            self._log_turn(state, "edit_error", f"Invalid JSON: {exc}", instruction)
            raise invalid_instruction("The AI returned an invalid response") from exc

        if not isinstance(update_dict, dict):
            self._log_turn(state, "edit_error", "Response was not a dict", instruction)
            raise invalid_instruction("Unexpected response format from AI")

        if not update_dict:
            self._log_turn(state, "edit_noop", "No fields returned", instruction)
            return {
                "updated_fields": [],
                "working_resume": wrk,
                "conversation_entry": state.conversation_log[-1],
            }

        # 4. Merge update into working resume
        try:
            full_dict = wrk.model_dump()
            full_dict.update(update_dict)
            state.working_resume = ParsedResume.model_validate(full_dict)
        except Exception as exc:
            logger.error("Failed to merge update: %s", exc)
            self._log_turn(state, "edit_error", f"Merge failed: {exc}", instruction)
            raise invalid_instruction(f"Could not apply changes: {exc}") from exc

        # 5. Log and persist
        changed = ", ".join(update_dict.keys())
        entry = self._log_turn(state, "edit", f"Updated fields: {changed}", instruction)
        await self._store.save(user_id, session_id, state)

        return {
            "updated_fields": list(update_dict.keys()),
            "working_resume": state.working_resume,
            "conversation_entry": entry,
        }

    # ── Pre-fetch helper ────────────────────────────────────────────

    def _prefetch(self, state: InteractiveResumeState, user_input: str) -> str:
        """Detect and fetch GitHub repos / job URLs in user input.

        Returns a context string to inject into the edit prompt.
        Note: this runs synchronously in the thread pool.
        """
        parts: list[str] = []

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
            except Exception as exc:
                logger.error("Failed to fetch project '%s': %s", repo, exc)

        sources = _extract_job_sources(user_input)
        for source, source_type in sources:
            try:
                output = (
                    JobParsingCrew()
                    .crew()
                    .kickoff(inputs={"source": source, "source_type": source_type})
                )
                job_req: JobRequirements = output.pydantic  # type: ignore[assignment]
                state.parsed_job_postings.append(job_req)
                parts.append(f"Queued job: {job_req.job_title} at {job_req.company}")
            except Exception as exc:
                logger.error("Failed to parse job '%s': %s", source, exc)

        return "\n".join(parts)

    # ── Conversation logging ────────────────────────────────────────

    def _log_turn(
        self,
        state: InteractiveResumeState,
        intent: str,
        summary: str,
        user_input: str = "",
    ) -> ConversationEntry:
        entry = ConversationEntry(
            timestamp=datetime.now(UTC).isoformat(),
            user_input=user_input,
            intent=intent,
            result_summary=summary,
        )
        state.conversation_log.append(entry)
        return entry

    # ── Job queue ───────────────────────────────────────────────────

    async def queue_job(
        self, user_id: str, session_id: str, url: str | None, text: str | None
    ) -> str:
        """Enqueue a job posting for later tailoring. Returns task_id."""
        state = await self.get_session(user_id, session_id)

        if url:
            source = url
            source_type = "url"
        elif text:
            source = text
            source_type = "text"
        else:
            raise AppError(
                400, "MISSING_SOURCE", "Provide a URL or job description text"
            )

        task_id = uuid.uuid4().hex
        _set_task(task_id, status="queued")

        async def _run() -> None:
            _set_task(task_id, status="running")
            try:
                output = await run_in_executor(
                    lambda: (
                        JobParsingCrew()
                        .crew()
                        .kickoff(inputs={"source": source, "source_type": source_type})
                    )
                )
                job_req: JobRequirements = output.pydantic  # type: ignore[assignment]
                state.parsed_job_postings.append(job_req)
                await self._store.save(user_id, session_id, state)
                _set_task(task_id, status="completed", result=job_req)
            except Exception as exc:
                logger.error("Job parsing failed: %s", exc)
                _set_task(
                    task_id,
                    status="failed",
                    error={"detail": str(exc), "error_code": "CREW_FAILURE"},
                )

        import asyncio

        asyncio.create_task(_run())
        return task_id

    async def queue_job_file(
        self, user_id: str, session_id: str, content: bytes, filename: str
    ) -> str:
        """Save an uploaded job file and enqueue parsing. Returns task_id."""
        state = await self.get_session(user_id, session_id)
        dest_dir = Path("uploads") / user_id / "files" / session_id / "jobs"

        def _write() -> Path:
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / filename
            dest.write_bytes(content)
            return dest

        filepath = await run_in_executor(_write)

        task_id = uuid.uuid4().hex
        _set_task(task_id, status="queued")

        async def _run() -> None:
            _set_task(task_id, status="running")
            try:
                output = await run_in_executor(
                    lambda: (
                        JobParsingCrew()
                        .crew()
                        .kickoff(
                            inputs={
                                "source": str(filepath),
                                "source_type": "file",
                            }
                        )
                    )
                )
                job_req: JobRequirements = output.pydantic  # type: ignore[assignment]
                state.parsed_job_postings.append(job_req)
                await self._store.save(user_id, session_id, state)
                _set_task(task_id, status="completed", result=job_req)
            except Exception as exc:
                logger.error("Job parsing failed: %s", exc)
                _set_task(
                    task_id,
                    status="failed",
                    error={"detail": str(exc), "error_code": "CREW_FAILURE"},
                )

        import asyncio

        asyncio.create_task(_run())
        return task_id

    async def list_jobs(self, user_id: str, session_id: str) -> list[JobRequirements]:
        """Get queued jobs for a session."""
        state = await self.get_session(user_id, session_id)
        return state.parsed_job_postings

    async def remove_job(self, user_id: str, session_id: str, job_index: int) -> None:
        """Remove a queued job by index."""
        state = await self.get_session(user_id, session_id)
        if 0 <= job_index < len(state.parsed_job_postings):
            state.parsed_job_postings.pop(job_index)
            await self._store.save(user_id, session_id, state)

    # ── Tailoring ───────────────────────────────────────────────────

    async def run_tailoring(self, user_id: str, session_id: str) -> str:
        """Enqueue resume tailoring against all queued jobs. Returns task_id."""
        state = await self.get_session(user_id, session_id)
        wrk = state.working_resume
        if wrk is None:
            raise no_resume_loaded()

        jobs = state.parsed_job_postings
        if not jobs:
            raise no_jobs_queued()

        task_id = uuid.uuid4().hex
        _set_task(
            task_id,
            status="queued",
            total_jobs=len(jobs),
            completed_jobs=0,
            errors=[],
        )

        async def _run() -> None:
            _set_task(task_id, status="running")
            try:
                outputs = await run_in_executor(
                    lambda: (
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
                )
                improved: list[ImprovedResume] = [
                    o.pydantic
                    for o in outputs  # type: ignore[assignment]
                ]
                for r in improved:
                    state.tailored_resumes.append(r.current_resume)
                await self._store.save(user_id, session_id, state)

                # Auto-generate .docx files so they're ready for download
                output_dir = Path("outputs") / user_id / session_id
                await run_in_executor(
                    lambda: self._render_resumes(state.tailored_resumes, output_dir)
                )

                _set_task(
                    task_id,
                    status="completed",
                    total_jobs=len(jobs),
                    completed_jobs=len(improved),
                )
                logger.info(
                    "Tailoring complete for session %s: %d resume(s)",
                    session_id,
                    len(improved),
                )
            except Exception as exc:
                logger.error("Tailoring failed: %s", exc)
                tasks = _TASK_STORE.get(task_id, {})
                errors: list[str] = tasks.get("errors", [])
                errors.append(str(exc))
                _set_task(
                    task_id,
                    status="failed",
                    total_jobs=len(jobs),
                    errors=errors,
                )

        import asyncio

        asyncio.create_task(_run())
        return task_id

    @staticmethod
    def _render_resumes(resumes: list, output_dir: Path) -> None:
        """Render .docx files for a list of tailored resumes. Runs in thread pool."""
        output_dir.mkdir(parents=True, exist_ok=True)
        for resume in resumes:
            try:
                render_resume(resume, output_dir)
            except Exception as exc:
                logger.error("Failed to render %s: %s", resume.output_filename(), exc)

    async def get_tailor_status(self, user_id: str, session_id: str) -> dict[str, Any]:
        """Return current tailoring progress for a session."""
        state = await self.get_session(user_id, session_id)
        return {
            "tailored_resumes": state.tailored_resumes,
            "total_jobs": len(state.parsed_job_postings),
        }

    # ── Task status ─────────────────────────────────────────────────

    def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """Return the current status of an async task."""
        return _get_task(task_id)

    # ── Export ──────────────────────────────────────────────────────

    async def export_resumes(
        self, user_id: str, session_id: str
    ) -> list[dict[str, Any]]:
        """Generate .docx files for all tailored resumes. Returns file info list."""
        state = await self.get_session(user_id, session_id)
        if not state.tailored_resumes:
            return []

        output_dir = Path("outputs") / user_id / session_id

        def _export() -> list[dict[str, Any]]:
            output_dir.mkdir(parents=True, exist_ok=True)
            results: list[dict[str, Any]] = []
            for resume in state.tailored_resumes:
                try:
                    path_str = render_resume(resume, output_dir)
                    path = Path(path_str)
                    results.append(
                        {
                            "filename": path.name,
                            "size": path.stat().st_size if path.exists() else 0,
                            "job_title": resume.job_title,
                            "company": resume.company,
                            "confidence_score": resume.confidence_score,
                        }
                    )
                except Exception as exc:
                    logger.error(
                        "Export failed for %s: %s", resume.output_filename(), exc
                    )
            return results

        return await run_in_executor(_export)

    async def get_exports(self, user_id: str, session_id: str) -> list[dict[str, Any]]:
        """List already-generated .docx files for a session."""
        output_dir = Path("outputs") / user_id / session_id

        def _list() -> list[dict[str, Any]]:
            if not output_dir.exists():
                return []
            results: list[dict[str, Any]] = []
            for p in sorted(
                output_dir.glob("*.docx"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            ):
                results.append(
                    {
                        "filename": p.name,
                        "size": p.stat().st_size,
                        "job_title": "",
                        "company": "",
                        "confidence_score": 0,
                    }
                )
            return results

        items = await run_in_executor(_list)

        # Augment with metadata from tailored resumes
        if items:
            state = await self.get_session(user_id, session_id)
            by_filename = {r.output_filename(): r for r in state.tailored_resumes}
            for item in items:
                match = by_filename.get(item["filename"])
                if match:
                    item["job_title"] = match.job_title
                    item["company"] = match.company
                    item["confidence_score"] = match.confidence_score
        return items

    async def get_export_path(
        self, user_id: str, session_id: str, filename: str
    ) -> Path | None:
        """Get the path to a generated .docx file. Returns None if not found."""
        path = Path("outputs") / user_id / session_id / filename

        def _exists(p: Path) -> bool:
            return p.exists() and p.is_file()

        if await run_in_executor(_exists, path):
            return path
        return None

    # ── Conversation history ────────────────────────────────────────

    async def get_conversation(
        self, user_id: str, session_id: str
    ) -> list[ConversationEntry]:
        """Get the full conversation log for a session."""
        state = await self.get_session(user_id, session_id)
        return state.conversation_log
