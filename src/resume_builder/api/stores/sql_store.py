"""SQLite-based session store — implements SessionStore ABC."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, func, select

from resume_builder.api.core.database import get_async_session_local
from resume_builder.api.models.session import Session
from resume_builder.api.stores.base import SessionStore, SessionSummary
from resume_builder.logger import get_logger
from resume_builder.models import InteractiveResumeState

logger = get_logger(__name__)


class SQLSessionStore(SessionStore):
    """Persists InteractiveResumeState as JSON in SQLite."""

    async def get(self, user_id: str, session_id: str) -> InteractiveResumeState | None:
        factory = get_async_session_local()
        async with factory() as db:
            result = await db.execute(
                select(Session).where(
                    Session.user_id == user_id, Session.id == session_id
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return InteractiveResumeState.model_validate_json(row.state_json)

    async def save(
        self, user_id: str, session_id: str, state: InteractiveResumeState
    ) -> None:
        factory = get_async_session_local()
        async with factory() as db:
            result = await db.execute(
                select(Session).where(
                    Session.user_id == user_id, Session.id == session_id
                )
            )
            row = result.scalar_one_or_none()
            state_json = state.model_dump_json()

            if row is not None:
                row.state_json = state_json
                row.updated_at = datetime.now(UTC)
            else:
                db.add(
                    Session(
                        id=session_id,
                        user_id=user_id,
                        state_json=state_json,
                    )
                )
            await db.commit()
            logger.debug("Saved session %s for user %s", session_id, user_id)

    async def list(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> tuple[list[SessionSummary], int]:
        factory = get_async_session_local()
        async with factory() as db:
            # Total count
            count_result = await db.execute(
                select(func.count())
                .select_from(Session)
                .where(Session.user_id == user_id)
            )
            total = count_result.scalar() or 0

            # Page
            result = await db.execute(
                select(Session)
                .where(Session.user_id == user_id)
                .order_by(Session.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )
            rows = result.scalars().all()

            summaries: list[SessionSummary] = []
            for row in rows:
                try:
                    state = InteractiveResumeState.model_validate_json(row.state_json)
                except Exception:
                    continue
                wrk = state.working_resume
                contact = wrk.contact if wrk else None
                summaries.append(
                    SessionSummary(
                        session_id=row.id,
                        candidate_name=contact.name if contact else "Unnamed",
                        skills_count=len(wrk.skills) if wrk else 0,
                        experience_count=len(wrk.experience) if wrk else 0,
                        job_count=len(state.parsed_job_postings),
                        tailored_count=len(state.tailored_resumes),
                        last_updated=row.updated_at.isoformat(),
                    )
                )

            return summaries, total

    async def delete(self, user_id: str, session_id: str) -> bool:
        factory = get_async_session_local()
        async with factory() as db:
            result = await db.execute(
                delete(Session).where(
                    Session.user_id == user_id, Session.id == session_id
                )
            )
            await db.commit()
            deleted = result.rowcount > 0
            if deleted:
                logger.debug("Deleted session %s for user %s", session_id, user_id)
            return deleted
