"""Async SQLAlchemy engine, session factory, and table creation."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from resume_builder.api.core.config import get_api_settings
from resume_builder.logger import get_logger

logger = get_logger(__name__)

settings = get_api_settings()
DATABASE_URL = f"sqlite+aiosqlite:///{settings.api_db_path}"

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


async def get_db():
    """FastAPI dependency: yield an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables. Called during app startup lifespan."""
    import resume_builder.api.models.refresh_token  # noqa: F401 — register ORM models
    import resume_builder.api.models.session  # noqa: F401
    import resume_builder.api.models.user  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created (if not exist)")
