"""
logger.py
---------
Centralised logging configuration for the Resume Builder.

All modules should obtain their logger via:
    from resume_builder.logger import get_logger
    logger = get_logger(__name__)

Log output:
    - File:  ./tmp/resume_builder.log (rotating, 5 MB max, 3 backups)
    - Console: only when LOG_LEVEL is DEBUG (stderr, custom format)
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from resume_builder.settings import settings

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_LOG_DIR = Path("./tmp")
_LOG_FILE = _LOG_DIR / "resume_builder.log"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 3

_configured = False

# Third-party loggers that tend to be noisy on the console.
# We bump them to WARNING so they don't clutter interactive output.
_NOISY_THIRD_PARTY_LOGGERS = [
    "crawl4ai",
    "httpx",
    "httpcore",
    "openai",
    "urllib3",
    "asyncio",
    "litellm",
    "crewai",
    "chromadb",
    "opentelemetry",
]


def configure_logging(level: str | None = None) -> None:
    """
    Set up the root logger for the entire package.

    Call this once at application startup (typically in main.py).
    Subsequent calls are no-ops.
    """
    global _configured
    if _configured:
        return
    _configured = True

    log_level = (level or settings.log_level).upper()

    # ── Silence noisy third-party loggers on the console ──────────────
    for name in _NOISY_THIRD_PARTY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    # ── Neutralise the root logger so third-party libs (CrewAI, crawl4ai)
    #    that call logging.basicConfig() / add StreamHandlers don't leak
    #    default-format messages to stderr. --------------------------------
    root_logger = logging.getLogger()
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)
    root_logger.addHandler(logging.NullHandler())

    # ── Package logger ────────────────────────────────────────────────
    pkg = logging.getLogger("resume_builder")
    pkg.setLevel(log_level)
    pkg.handlers.clear()
    pkg.propagate = False  # don't bubble up to the (now-null) root logger

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # ── File handler (always active) ──────────────────────────────────
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    pkg.addHandler(file_handler)

    # ── Console handler (only in DEBUG mode, stderr) ──────────────────
    if log_level == "DEBUG":
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        pkg.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger scoped under the 'resume_builder' namespace."""
    # Normalise: "resume_builder.tools.job_scraper" → "resume_builder.job_scraper"
    if name.startswith("resume_builder."):
        parts = name.split(".")
        short = f"{parts[0]}.{parts[-1]}" if len(parts) > 2 else name
    else:
        short = f"resume_builder.{name}"
    return logging.getLogger(short)
