"""Thread pool for running synchronous CrewAI / LLM operations."""

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from resume_builder.logger import get_logger

logger = get_logger(__name__)

_executor: ThreadPoolExecutor | None = None


def create_worker_pool(max_workers: int = 2) -> None:
    """Initialise the thread pool. Called during FastAPI lifespan startup."""
    global _executor
    _executor = ThreadPoolExecutor(max_workers=max_workers)
    logger.info("Worker pool created with %d threads", max_workers)


async def shutdown_worker_pool() -> None:
    """Shut down the thread pool. Called during FastAPI lifespan shutdown."""
    global _executor
    if _executor is not None:
        logger.info("Shutting down worker pool")
        _executor.shutdown(wait=True)
        _executor = None


async def run_in_executor(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run a synchronous function in the thread pool, awaiting its result.

    Use this to bridge CrewAI's synchronous .kickoff() / LLM.call()
    into the async FastAPI world without blocking the event loop.

    Raises RuntimeError if the worker pool hasn't been initialised.
    """
    if _executor is None:
        raise RuntimeError("Worker pool not initialised — check lifespan setup")
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, lambda: fn(*args, **kwargs))
