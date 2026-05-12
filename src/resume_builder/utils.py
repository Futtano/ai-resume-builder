from docxtpl import DocxTemplate
from pathlib import Path
from resume_builder.models import TailoredResume

TEMPLATE = Path("templates/resume_template.docx")


def render_resume(resume: TailoredResume, output_dir: Path) -> str:
    """Renders the resume template. Returns the output .docx path."""
    tpl = DocxTemplate(TEMPLATE)
    tpl.render(resume.model_dump())  # Pydantic → dict, keys match template exactly
    out = (
        output_dir
        / f"resume_{resume.job_title.replace(' ', '_')}_{resume.company.replace(' ', '_')}.docx"
    )
    out.parent.mkdir(exist_ok=True)
    tpl.save(out)
    return str(out)
