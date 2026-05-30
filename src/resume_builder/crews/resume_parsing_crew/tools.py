"""
resume_parsing_crew/tools.py
----------------------------
Local tools for extracting structured text from resume PDFs.
"""

from pathlib import Path
from typing import Literal

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ExtractResumeContentInput(BaseModel):
    """Arguments accepted by the resume PDF extraction tool."""

    pdf_path: str = Field(description="Absolute or relative path to the resume PDF")
    output_format: Literal["markdown", "text"] = Field(
        default="markdown",
        description="Extraction format. Use markdown by default unless plain text is explicitly needed.",
    )


class ExtractResumeContentTool(BaseTool):
    """Extract text or markdown from a local resume PDF using PyMuPDF4LLM."""

    name: str = "extract_resume_content"
    description: str = (
        "Extract text from a local resume PDF file. "
        "Use this when a resume_pdf_path is provided. "
        "Set output_format='markdown' for layout-aware extraction, or "
        "output_format='text' for plain text."
    )
    args_schema: type[BaseModel] = ExtractResumeContentInput

    def _run(self, pdf_path: str, output_format: Literal["markdown", "text"]) -> str:
        import pymupdf4llm

        path = Path(pdf_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Resume PDF not found: {path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a PDF file, got: {path.suffix}")

        if output_format == "markdown":
            content = pymupdf4llm.to_markdown(str(path))
        else:
            content = pymupdf4llm.to_text(str(path))

        if not content or not content.strip():
            raise RuntimeError(f"No extractable content returned for {path.name}")

        return content
