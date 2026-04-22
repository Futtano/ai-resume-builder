"""
test_resume_processor.py
------------------------
Tests for ResumeProcessor (PDF extraction and text cleaning).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from resume_builder.processors.resume import ResumeProcessor


class TestResumeProcessor:
    def test_clean_text_normalises_ligatures(self) -> None:
        processor = ResumeProcessor()
        text = "ﬁ ﬂ ﬀ ﬃ ﬄ"
        cleaned = processor._clean_text(text)
        assert cleaned == "fi fl ff ffi ffl"

    def test_clean_text_removes_soft_hyphens(self) -> None:
        processor = ResumeProcessor()
        text = "soft\u00adhyphen"
        cleaned = processor._clean_text(text)
        assert cleaned == "softhyphen"

    def test_clean_text_collapses_excess_newlines(self) -> None:
        processor = ResumeProcessor()
        text = "Line 1\n\n\n\nLine 2"
        cleaned = processor._clean_text(text)
        assert cleaned == "Line 1\n\nLine 2"

    def test_clean_text_strips_line_whitespace(self) -> None:
        processor = ResumeProcessor()
        text = "  spaced line  \n  another line  "
        cleaned = processor._clean_text(text)
        assert cleaned == "  spaced line\n  another line"

    def test_clean_text_joins_hyphenated_words(self) -> None:
        processor = ResumeProcessor()
        text = "multi-\npage"
        cleaned = processor._clean_text(text)
        assert cleaned == "multipage"

    def test_from_pdf_nonexistent_file(self) -> None:
        processor = ResumeProcessor()
        with pytest.raises(FileNotFoundError):
            processor.from_pdf(Path("nonexistent.pdf"))

    def test_from_pdf_wrong_extension(self, tmp_path: Path) -> None:
        processor = ResumeProcessor()
        txt_file = tmp_path / "resume.txt"
        txt_file.write_text("not a pdf")
        with pytest.raises(ValueError, match="Expected a .pdf"):
            processor.from_pdf(txt_file)

    @patch("resume_builder.processors.resume.ResumeProcessor._extract_with_pymupdf")
    @patch("resume_builder.processors.resume.ResumeProcessor._extract_with_pypdf")
    def test_from_pdf_fallback_logic(
        self, mock_pypdf: MagicMock, mock_pymupdf: MagicMock, tmp_path: Path
    ) -> None:
        pdf_path = tmp_path / "resume.pdf"
        pdf_path.write_text("fake pdf")

        # Case 1: PyMuPDF succeeds with enough text
        mock_pymupdf.return_value = "Long enough resume text" * 10
        processor = ResumeProcessor().from_pdf(pdf_path)
        assert "Long enough" in processor.extracted
        assert mock_pypdf.call_count == 0

        # Case 2: PyMuPDF returns too little, pypdf used
        mock_pymupdf.return_value = "too short"
        mock_pypdf.return_value = "Long enough resume text" * 10
        processor = ResumeProcessor().from_pdf(pdf_path)
        assert mock_pypdf.call_count == 1
        assert "Long enough" in processor.extracted

    @patch("resume_builder.processors.resume.ResumeProcessor._extract_with_pymupdf")
    @patch("resume_builder.processors.resume.ResumeProcessor._extract_with_pypdf")
    def test_from_pdf_fails_if_empty(
        self, mock_pypdf: MagicMock, mock_pymupdf: MagicMock, tmp_path: Path
    ) -> None:
        pdf_path = tmp_path / "resume.pdf"
        pdf_path.write_text("fake pdf")

        mock_pymupdf.return_value = ""
        mock_pypdf.return_value = "short"
        with pytest.raises(RuntimeError, match="Could not extract"):
            ResumeProcessor().from_pdf(pdf_path)
