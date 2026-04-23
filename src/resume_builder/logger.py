"""
logger.py
---------
Centralised logging configuration for the Resume Builder.

All modules should obtain their logger via:
    from resume_builder.logger import get_logger
    logger = get_logger(__name__)

Log output:
    - File:  ./tmp/resume_builder.log (rotating, 5 MB max, 3 backups)
    - Console: only when LOG_LEVEL is DEBUG (stderr)
"""

from __future__ import annotations

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

    root = logging.getLogger("resume_builder")
    root.setLevel(log_level)
    root.handlers.clear()  # avoid duplicate handlers on re-runs

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
    root.addHandler(file_handler)

    # ── Console handler (only in DEBUG mode, stderr) ──────────────────
    if log_level == "DEBUG":
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger scoped under the 'resume_builder' namespace."""
    # Normalise: "resume_builder.tools.job_scraper" → "resume_builder.job_scraper"
    if name.startswith("resume_builder."):
        short = name.replace("resume_builder.", "resume_builder.", 1)
    else:
        short = f"resume_builder.{name}"
    return logging.getLogger(short)
