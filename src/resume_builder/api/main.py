"""FastAPI application factory and lifespan management."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from resume_builder.api.core.config import get_api_settings
from resume_builder.api.core.workers import create_worker_pool, shutdown_worker_pool
from resume_builder.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create worker pool. Shutdown: drain and destroy pool."""
    settings = get_api_settings()
    create_worker_pool(max_workers=settings.api_max_workers)
    logger.info("API server started (workers=%d)", settings.api_max_workers)
    yield
    await shutdown_worker_pool()
    logger.info("API server shut down")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_api_settings()

    app = FastAPI(
        title="Resume Builder API",
        description="AI-powered resume tailoring — interactive and batch",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ── CORS (Svelte dev server) ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ──
    from resume_builder.api.errors import register_handlers

    register_handlers(app)

    # ── API routes ──
    from resume_builder.api.v1.router import api_router

    app.include_router(api_router, prefix="/api/v1")

    # ── Health check (no auth required) ──
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
