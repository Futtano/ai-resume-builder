"""
pdf_extractor.py
----------------

Custom CrewAI tool for extracting clean text form PDF files.

Uses PyMuPDF (fitz) as the primary extractor - it handles complex layouts,
multi-column PDFs, and embedded fonts much better than most alternatives.
Falls back to pypdf if PyMuPDF is not available.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class PDFExtractorInput(BaseModel):
    """Input schema for the PDF extractor tool."""

    file_path: str = Field(description="Absolute or relative path to the PDF file")


class PDFExtractorTool(BaseTool):
    """
    Extract clean, structured text from a PDF resume.

    Attempts PyMuPDF first (best qaulity), then falls back to pypdf.
    Post-processes the extracted text to remove common PDF artefacts
    (ligatures, hyphenation, excessive whitespace) that confuse LLMs.
    """

    name: str = "PDF Text Extractor"
    description: str = (
        "Extracts the full text content from a PDF file. "
        "Use this to read a resume PDF before parsing it. "
        "Input: the file path to the PDF. "
        "Output: clean text content of the entire document"
    )
    args_schema: Type[BaseModel] = PDFExtractorInput

    def _run(self, file_path: str) -> str:
        path = Path(file_path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a .pdf file, got: {path.suffix}")

        text = self._extract_with_pymupdf(path)
        if not text or len(text.strip()) < 100:
            # PyMuPDF returned too little - try fallback
            text = self._extract_with_pypdf(path)

        if not text or len(text.strip()) < 50:
            raise RuntimeError(
                f"Could not extract meaningful text from {path.name}. "
                "The PDF may be scanned/image-based."
            )

        return self._clean_text(text)

    # ------------------------------------------------------------
    # Extraction backends
    # ------------------------------------------------------------

    def _extract_with_pymupdf(self, path: Path) -> Optional[str]:
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(path))
            pages: list[str] = []
            for page in doc:
                # 'text' mode preserves reading order best for resumes
                pages.append(page.get_text("text"))  # type: ignore[attr-defined]
            doc.close()
            return "\n".join(pages)
        except ImportError:
            return None
        except Exception as exc:
            # Log but do not crash - let the fallback try
            print(f"[PDFExtractor] PyMuPDF error: {exc}")
            return None

    def _extract_with_pypdf(self, path: Path) -> Optional[str]:
        try:
            from pypdf import PdfReader  # type: ignore[import]

            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)
        except ImportError:
            return None
        except Exception as exc:
            print(f"[PDFExtractor] pypdf error: {exc}")
            return None

    # ------------------------------------------------------------
    # Post-processing
    # ------------------------------------------------------------

    def _clean_text(self, text: str) -> str:
        """Remove common PDF extraction artefacts"""
        # Normalise ligatures (fi, fl, ff, ffi, ffl)
        ligatures = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}
        for lig, replacement in ligatures.items():
            text = text.replace(lig, replacement)

        # Remove soft hyphens and zero-width characters
        text = text.replace("\u00ad", "").replace("\u200b", "")

        # Normalise line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Collapse hyphenated words split across lines.
        # Only match when a hyphen ends a word fragment (no leading space/bullet),
        # to avoid stripping list bullets like "- Python".
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

        # Collapse excessive blank lines (> 2 consecutive)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Strip leading/trailing whitespace from each line
        lines = [line.rstrip() for line in text.splitlines()]
        text = "\n".join(lines)

        return text
