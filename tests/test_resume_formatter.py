"""
test_resume_formatter.py
------------------------
Tests for ResumeFormatterTool — .docx generation from TailoredResume model.
"""

from __future__ import annotations

from pathlib import Path

from docx import Document

from resume_builder.models import (
    ContactInfo,
    EducationEntry,
    TailoredExperienceEntry,
    TailoredResume,
)
from resume_builder.tools.resume_formatter import ResumeFormatterTool


class TestResumeFormatter:
    def setup_method(self) -> None:
        self.formatter = ResumeFormatterTool()

    def _make_resume(self) -> TailoredResume:
        return TailoredResume(
            contact=ContactInfo(
                name="Alice Smith",
                email="alice@example.com",
                phone="+1-555-0100",
            ),
            professional_summary="Backend engineer with 5+ years of experience.",
            experience=[
                TailoredExperienceEntry(
                    company="TechCorp",
                    role="Senior Engineer",
                    start_date="Jan 2022",
                    end_date="Present",
                    location="Milan",
                    bullets=[
                        "Built microservices",
                        "Led migration to Go",
                    ],
                ),
            ],
            skills=["Python", "Go", "Docker"],
            education=[
                EducationEntry(
                    institution="Politecnico di Milano",
                    degree="Master's",
                    field_of_study="CS",
                    start_date="2016",
                    end_date="2020",
                ),
            ],
            company="CloudScale",
            job_title="Platform Engineer",
            confidence_score=85,
            tailoring_notes="Tailored for platform role.",
            session_id=1,
            ats_keyword_coverage=["python", "go", "docker"],
        )

    def test_generates_docx(self, tmp_dir: Path) -> None:
        resume = self._make_resume()
        path = self.formatter.generate(resume, output_dir=tmp_dir)

        assert path.exists()
        assert path.suffix == ".docx"
        assert path.name == "resume_CloudScale_Platform_Engineer.docx"

    def test_docx_is_readable(self, tmp_dir: Path) -> None:
        resume = self._make_resume()
        path = self.formatter.generate(resume, output_dir=tmp_dir)

        doc = Document(str(path))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

        full_text = " ".join(paragraphs)
        assert "Alice Smith" in full_text
        # The experience company (TechCorp) appears in the body
        assert "TechCorp" in full_text
        assert "Platform Engineer" not in full_text  # target job title, not shown
        assert "Backend engineer" in full_text

    def test_output_dir_created(self, tmp_dir: Path) -> None:
        resume = self._make_resume()
        nested = tmp_dir / "sub" / "dir"
        path = self.formatter.generate(resume, output_dir=nested)

        assert path.exists()
        assert path.parent == nested

    def test_with_certifications(self, tmp_dir: Path) -> None:
        resume = self._make_resume()
        resume.certifications = ["AWS Solutions Architect", "CKA"]
        path = self.formatter.generate(resume, output_dir=tmp_dir)

        doc = Document(str(path))
        full_text = " ".join(p.text for p in doc.paragraphs)
        assert "CERTIFICATIONS" in full_text.upper()
        assert "AWS Solutions Architect" in full_text
