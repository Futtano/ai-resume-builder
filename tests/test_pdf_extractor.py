"""
test_pdf_extractor.py
---------------------
Tests for the PDFExtractorTool with mocked fitz/pypdf backends.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from resume_builder.tools.pdf_extractor import PDFExtractorTool


class TestPDFExtractor:
    def setup_method(self) -> None:
        self.extractor = PDFExtractorTool()

    def test_missing_file_raises(self, tmp_dir: Path) -> None:
        missing = tmp_dir / "does_not_exist.pdf"
        with pytest.raises(FileNotFoundError):
            self.extractor._run(str(missing))

    def test_wrong_extension_raises(self, tmp_dir: Path) -> None:
        bad = tmp_dir / "resume.txt"
        bad.write_text("hello")
        with pytest.raises(ValueError, match="Expected a .pdf file"):
            self.extractor._run(str(bad))

    def test_pymupdf_extraction(self, tmp_dir: Path) -> None:
        """Test successful extraction via mocked PyMuPDF."""
        pdf_path = tmp_dir / "test.pdf"
        pdf_path.write_bytes(b"fake pdf content")

        mock_page = MagicMock()
        mock_page.get_text.return_value = (
            "John Smith\nSenior Engineer\nExperience: "
            "Built microservices at TechCorp. "
            "Skills: Python, Go, Docker, Kubernetes, AWS."
        )

        mock_doc = MagicMock()
        mock_doc.__iter__ = lambda self: iter([mock_page])

        with patch("fitz.Document", return_value=mock_doc):
            with patch("fitz.open", return_value=mock_doc):
                text = self.extractor._run(str(pdf_path))

        assert "John Smith" in text
        assert len(text) > 50

    def test_pypdf_fallback(self, tmp_dir: Path) -> None:
        """Test pypdf fallback when PyMuPDF returns too little text."""
        pdf_path = tmp_dir / "test.pdf"
        pdf_path.write_bytes(b"fake pdf content")

        mock_reader = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = (
            "Jane Doe\nBackend Developer\n5 years experience. "
            "Skills: Python, Django, PostgreSQL."
        )
        mock_reader.pages = [mock_page]

        with patch("fitz.Document"):
            with patch("fitz.open") as mock_open:
                empty_doc = MagicMock()
                empty_doc.__iter__ = lambda self: iter([])
                mock_open.return_value = empty_doc

                with patch("pypdf.PdfReader", return_value=mock_reader):
                    text = self.extractor._run(str(pdf_path))

        assert "Jane Doe" in text

    def test_image_pdf_raises(self, tmp_dir: Path) -> None:
        """Test error when PDF has no extractable text."""
        pdf_path = tmp_dir / "scanned.pdf"
        pdf_path.write_bytes(b"fake scanned pdf")

        with patch("fitz.Document"):
            with patch("fitz.open") as mock_open:
                empty_doc = MagicMock()
                empty_doc.__iter__ = lambda self: iter([])
                mock_open.return_value = empty_doc

                with patch("pypdf.PdfReader") as mock_pypdf:
                    mock_pypdf.return_value.pages = []

                    with pytest.raises(RuntimeError, match="Could not extract"):
                        self.extractor._run(str(pdf_path))

    def test_clean_text_removes_artefacts(self) -> None:
        """Test PDF text cleaning removes ligatures and hyphenation."""
        raw = (
            "Pro-ﬁciency\nin Python and ﬂuent\nin Go. "
            "Experi- enced\nwith distributed systems."
        )
        cleaned = self.extractor._clean_text(raw)
        assert "Pro-ficiency" in cleaned
        assert "fluent" in cleaned
        assert "\n\n" not in cleaned.strip()
