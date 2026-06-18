"""Session ORM model — persisted InteractiveResumeState."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from resume_builder.api.core.database import Base, utcnow


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(8),
        primary_key=True,
        default=lambda: uuid.uuid4().hex[:8],
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    state_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )
