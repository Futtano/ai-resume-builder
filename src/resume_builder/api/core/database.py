"""Async SQLAlchemy engine, session factory, and table creation."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from resume_builder.api.core.config import get_api_settings
from resume_builder.logger import get_logger

logger = get_logger(__name__)

_engine = None
_AsyncSessionLocal = None


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


def _get_database_url() -> str:
    settings = get_api_settings()
    if settings.api_db_path == ":memory:":
        return "sqlite+aiosqlite://"
    return f"sqlite+aiosqlite:///{settings.api_db_path}"


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(_get_database_url(), echo=False)
    return _engine


def get_async_session_local():
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _AsyncSessionLocal


def reset_db() -> None:
    """Reset the engine and session factory (for testing)."""
    global _engine, _AsyncSessionLocal
    _engine = None
    _AsyncSessionLocal = None
    get_api_settings.cache_clear()  # type: ignore[attr-defined]


async def get_db():
    """FastAPI dependency: yield an async database session."""
    factory = get_async_session_local()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables. Called during app startup lifespan."""
    import resume_builder.api.models.refresh_token  # noqa: F401 — register ORM models
    import resume_builder.api.models.session  # noqa: F401
    import resume_builder.api.models.user  # noqa: F401

    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created (if not exist)")
