"""File-based session store — JSON persistence with LRU read cache."""

from __future__ import annotations

import json
import shutil
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path

from resume_builder.api.core.workers import run_in_executor
from resume_builder.api.stores.base import SessionStore, SessionSummary
from resume_builder.logger import get_logger
from resume_builder.models import InteractiveResumeState

logger = get_logger(__name__)


class FileSessionStore(SessionStore):
    """Stores sessions as JSON files on disk, scoped by user_id.

    Matches the pattern used by InteractiveResumeFlow._save_state().
    Adds an in-memory LRU cache so repeated reads during active editing
    don't hit disk.
    """

    def __init__(
        self,
        base_dir: Path | None = None,
        cache_size: int = 100,
    ) -> None:
        self._base = (base_dir or Path("uploads")).resolve()
        self._cache: OrderedDict[str, InteractiveResumeState] = OrderedDict()
        self._cache_size = cache_size

    # ── Public API ──

    async def get(self, user_id: str, session_id: str) -> InteractiveResumeState | None:
        """Load session state from cache or disk."""
        cache_key = f"{user_id}:{session_id}"

        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key]

        path = self._session_path(user_id, session_id)
        if not await run_in_executor(path.exists):
            return None

        content = await run_in_executor(path.read_text)
        state = InteractiveResumeState.model_validate_json(content)
        self._cache_set(cache_key, state)
        return state

    async def save(
        self, user_id: str, session_id: str, state: InteractiveResumeState
    ) -> None:
        """Persist session to disk and cache."""
        cache_key = f"{user_id}:{session_id}"
        self._cache_set(cache_key, state)

        path = self._session_path(user_id, session_id)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Write to temp file first, then rename (atomic on same fs)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(state.model_dump_json(indent=2))
            tmp.replace(path)
            # Write backup
            bak = path.with_suffix(".json.bak")
            shutil.copy2(path, bak)

        await run_in_executor(_write)
        logger.debug("Saved session %s for user %s", session_id, user_id)

    async def list(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> tuple[list[SessionSummary], int]:
        """List sessions for a user, newest first."""
        sess_dir = self._base / user_id / "sessions"

        if not await run_in_executor(sess_dir.exists):
            return [], 0

        paths = sorted(
            [p for p in await run_in_executor(sess_dir.iterdir) if p.suffix == ".json"],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        total = len(paths)
        page = paths[offset : offset + limit]

        summaries: list[SessionSummary] = []
        for p in page:
            try:
                data = json.loads(await run_in_executor(p.read_text))
            except (json.JSONDecodeError, OSError):
                continue
            wrk = data.get("working_resume") or {}
            contact = wrk.get("contact") or {}
            summaries.append(
                SessionSummary(
                    session_id=p.stem,
                    candidate_name=contact.get("name", "Unnamed"),
                    skills_count=len(wrk.get("skills", [])),
                    experience_count=len(wrk.get("experience", [])),
                    job_count=len(data.get("parsed_job_postings", [])),
                    tailored_count=len(data.get("tailored_resumes", [])),
                    last_updated=datetime.fromtimestamp(
                        p.stat().st_mtime, tz=UTC
                    ).isoformat(),
                )
            )

        return summaries, total

    async def delete(self, user_id: str, session_id: str) -> bool:
        """Delete session JSON and uploaded files. Returns True if it existed."""
        cache_key = f"{user_id}:{session_id}"
        self._cache.pop(cache_key, None)

        session_dir = self._base / user_id / "files" / session_id
        json_path = self._session_path(user_id, session_id)
        existed = False

        if await run_in_executor(session_dir.exists):
            await run_in_executor(shutil.rmtree, session_dir)
            existed = True

        if await run_in_executor(json_path.exists):
            json_path.unlink()
            bak = json_path.with_suffix(".json.bak")
            if bak.exists():
                bak.unlink()
            existed = True

        return existed

    # ── Helpers ──

    def _session_path(self, user_id: str, session_id: str) -> Path:
        return self._base / user_id / "sessions" / f"{session_id}.json"

    def _cache_set(self, key: str, state: InteractiveResumeState) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            self._cache[key] = state
            while len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)
