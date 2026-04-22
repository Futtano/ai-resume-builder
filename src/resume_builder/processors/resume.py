"""
resume.py
---------
Processor for extracting raw text from resume files (PDF, Text).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from resume_builder.logger import get_logger

logger = get_logger(__name__)


class ResumeProcessor:
    """
    Handles the extraction of raw text from resume sources.
    """

    def __init__(self) -> None:
        self._extracted: str = ""

    @property
    def extracted(self) -> str:
        """The extracted raw text."""
        return self._extracted

    def from_text(self, text: str) -> ResumeProcessor:
        """Load resume directly from text."""
        self._extracted = text
        return self

    def from_pdf(self, path: Path) -> ResumeProcessor:
        """Extract text from a PDF file."""
        path = path.resolve()
        logger.info("Extracting text from PDF: %s", path.name)

        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a .pdf file, got: {path.suffix}")

        text = self._extract_with_pymupdf(path)
        if not text or len(text.strip()) < 100:
            logger.debug("PyMuPDF extracted too little, trying pypdf fallback")
            text = self._extract_with_pypdf(path)

        if not text or len(text.strip()) < 50:
            raise RuntimeError(
                f"Could not extract meaningful text from {path.name}. "
                "The PDF may be scanned/image-based."
            )

        self._extracted = self._clean_text(text)
        logger.info("Extracted %d chars (%d after cleaning)", len(text), len(self._extracted))
        return self

    def _extract_with_pymupdf(self, path: Path) -> Optional[str]:
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(path))
            pages: list[str] = []
            for page in doc:
                pages.append(page.get_text("text"))
            doc.close()
            return "\n".join(pages)
        except ImportError:
            return None
        except Exception as exc:
            logger.debug("PyMuPDF failed: %s", exc)
            return None

    def _extract_with_pypdf(self, path: Path) -> Optional[str]:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)
        except ImportError:
            return None
        except Exception as exc:
            logger.debug("pypdf failed: %s", exc)
            return None

    def _clean_text(self, text: str) -> str:
        """Remove common PDF extraction artefacts"""
        ligatures = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}
        for lig, replacement in ligatures.items():
            text = text.replace(lig, replacement)

        text = text.replace("\u00ad", "").replace("\u200b", "")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        lines = [line.rstrip() for line in text.splitlines()]
        return "\n".join(lines)
