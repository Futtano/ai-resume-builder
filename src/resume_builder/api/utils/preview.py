"""Resume preview utility — renders ParsedResume to .docx bytes via docxtpl.

The pipeline: ParsedResume → dict (w/ placeholders) → temp .docx → bytes.
The frontend renders the .docx bytes in-browser using the docx-preview library.
"""

from __future__ import annotations

import io
from pathlib import Path

from docxtpl import DocxTemplate

from resume_builder.models import ContactInfo, ParsedResume

TEMPLATE = Path("templates/resume_template.docx")

# ── Placeholder dictionary for all resume sections ──────────────────────


def _empty_contact() -> ContactInfo:
    return ContactInfo(
        name="Unnamed Candidate",
        email="[email]",
        phone="[phone]",
        location="[location]",
    )


def _empty_experience() -> list[dict]:
    return [
        {
            "role": "[Job Title]",
            "company": "[Company]",
            "start_date": "[Start]",
            "end_date": "[End]",
            "location": "[Location]",
            "bullets": ["[Describe your accomplishments and responsibilities here]"],
        }
    ]


def _empty_education() -> list[dict]:
    return [
        {
            "institution": "[Institution]",
            "degree": "[Degree]",
            "field_of_study": "[Field of Study]",
            "start_date": "[Start]",
            "end_date": "[End]",
            "degree_mark": "",
            "honours": "",
        }
    ]


def _empty_projects() -> list[dict]:
    return [
        {
            "repo_name": "[Project Name]",
            "repo_url": "",
            "description": "[Project description]",
            "tech_stack": ["[Tech stack]"],
            "architecture": "[Architecture overview]",
            "stars": 0,
        }
    ]


def _prepare_data(resume: ParsedResume) -> dict:
    """Build a template-ready dict, injecting placeholders for empty fields."""
    data = resume.model_dump()

    # Top-level strings
    if not data.get("professional_summary", "").strip():
        data["professional_summary"] = (
            "[Add a professional summary describing your background and career goals]"
        )

    # Lists — show at least one placeholder entry so all template sections appear
    if not data.get("skills"):
        data["skills"] = ["[Add your technical skills here]"]

    if not data.get("experience"):
        data["experience"] = _empty_experience()

    if not data.get("education"):
        data["education"] = _empty_education()

    # Conditional sections: inject placeholder if empty so the template renders them
    if not data.get("projects"):
        data["projects"] = _empty_projects()

    if not data.get("certifications"):
        data["certifications"] = ["[Add certifications here]"]

    if not data.get("publications"):
        data["publications"] = [
            {
                "title": "[Publication Title]",
                "venue": "[Venue]",
                "date": "[Date]",
                "publisher": "",
                "link": "",
            }
        ]

    if not data.get("workshops"):
        data["workshops"] = [
            {
                "title": "[Workshop Title]",
                "date": "[Date]",
                "place": "[Place]",
            }
        ]

    if not data.get("awards"):
        data["awards"] = [
            {
                "title": "[Award Title]",
                "organization": "[Organization]",
                "date": "[Date]",
            }
        ]

    if not data.get("international_experiences"):
        data["international_experiences"] = [
            {
                "place": "[Location]",
                "date": "[Date]",
                "description": "[Description of international experience]",
            }
        ]

    # Ensure contact has defaults
    contact = data.get("contact") or {}
    for field in ("email", "phone", "location"):
        if not contact.get(field, "").strip():
            contact[field] = f"[{field}]"
    data["contact"] = contact

    return data


def render_resume_preview_docx(resume: ParsedResume) -> bytes:
    """Render a ParsedResume to .docx bytes via docxtpl.

    1. Build template-ready dict with placeholders for empty fields.
    2. Render to an in-memory .docx via DocxTemplate.
    3. Return the raw bytes for client-side rendering with docx-preview.
    """
    data = _prepare_data(resume)

    tpl = DocxTemplate(TEMPLATE)
    tpl.render(data)

    buf = io.BytesIO()
    tpl.save(buf)
    return buf.getvalue()


def render_resume_preview_docx_or_placeholder(resume: ParsedResume | None) -> bytes:
    """Render a preview .docx, or a placeholder template if resume is None."""
    if resume is None:
        empty = ParsedResume(
            contact=_empty_contact(),
            professional_summary="",
            experience=[],
            skills=[],
            education=[],
            certifications=[],
            projects=[],
            publications=[],
            workshops=[],
            awards=[],
            international_experiences=[],
        )
        return render_resume_preview_docx(empty)
    return render_resume_preview_docx(resume)
