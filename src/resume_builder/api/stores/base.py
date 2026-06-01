"""SessionStore abstract interface — repository pattern for session persistence."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from resume_builder.models import InteractiveResumeState


@dataclass
class SessionSummary:
    """Lightweight summary returned by list_sessions()."""

    session_id: str
    candidate_name: str
    skills_count: int
    experience_count: int
    job_count: int
    tailored_count: int
    last_updated: str  # ISO 8601


class SessionStore(ABC):
    """Async interface for session persistence.

    The async signatures allow swapping to an async database (SQLite, etc.)
    without changing any caller code. The file-based implementation wraps
    synchronous I/O in run_in_executor internally.
    """

    @abstractmethod
    async def get(self, user_id: str, session_id: str) -> InteractiveResumeState | None:
        """Load a session by user and session ID. Returns None if not found."""
        ...

    @abstractmethod
    async def save(
        self, user_id: str, session_id: str, state: InteractiveResumeState
    ) -> None:
        """Persist session state. Creates parent directories if needed."""
        ...

    @abstractmethod
    async def list(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> tuple[list[SessionSummary], int]:
        """List sessions for a user, newest first. Returns (items, total)."""
        ...

    @abstractmethod
    async def delete(self, user_id: str, session_id: str) -> bool:
        """Delete a session and its files. Returns True if it existed."""
        ...
