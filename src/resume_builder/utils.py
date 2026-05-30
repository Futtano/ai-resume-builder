"""
utils.py
--------
Utility functions for the Resume Builder, including .docx rendering.
"""

from pathlib import Path

from docxtpl import DocxTemplate

from resume_builder.models import TailoredResume

TEMPLATE = Path("templates/resume_template.docx")


def render_resume(resume: TailoredResume, output_dir: Path) -> str:
    """Renders the resume template. Returns the output .docx path."""
    tpl = DocxTemplate(TEMPLATE)
    tpl.render(resume.model_dump())  # Pydantic → dict, keys match template exactly
    out = output_dir / resume.output_filename()
    out.parent.mkdir(exist_ok=True)
    tpl.save(out)
    return str(out)
