"""
test_models.py
--------------
Tests for Pydantic model validation, defaults, and edge cases.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from resume_builder.models import (
    AwardEntry,
    ContactInfo,
    EducationEntry,
    ExperienceEntry,
    InternationalExperienceEntry,
    ParsedResume,
    PublicationEntry,
    TailoredExperienceEntry,
    TailoredResume,
    WorkshopEntry,
)


class TestContactInfo:
    def test_minimal_valid(self) -> None:
        c = ContactInfo(name="Bob")
        assert c.name == "Bob"
        assert c.email == ""

    def test_all_fields(self) -> None:
        c = ContactInfo(
            name="Alice",
            email="a@b.com",
            phone="+1-555-0100",
            location="Milan",
            linkedin="linkedin.com/in/a",
            github="github.com/a",
            portfolio="a.dev",
        )
        assert c.name == "Alice"
        assert c.email == "a@b.com"

    def test_missing_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            ContactInfo()  # type: ignore[call-arg]


class TestExperienceEntry:
    def test_minimal_valid(self) -> None:
        e = ExperienceEntry(
            company="Acme",
            role="Engineer",
            start_date="2020",
            end_date="Present",
            bullets=["Did stuff"],
            skills_demonstrated=["Python"],
        )
        assert e.company == "Acme"
        assert e.location == ""

    def test_missing_required_raises(self) -> None:
        with pytest.raises(ValidationError):
            ExperienceEntry(
                company="Acme",
                role="Engineer",
                start_date="2020",
                end_date="Present",
            )  # type: ignore[call-arg]


class TestEducationEntry:
    def test_minimal_valid(self) -> None:
        e = EducationEntry(
            institution="Uni",
            degree="Bachelor's",
            field_of_study="CS",
            start_date="2016",
            end_date="2020",
        )
        assert e.institution == "Uni"
        assert e.degree_mark == ""

    def test_missing_field_raises(self) -> None:
        """Missing one of the required fields (institution, degree, field_of_study, dates)."""
        with pytest.raises(ValidationError):
            EducationEntry(
                institution="Uni",
                degree="BS",
                # missing field_of_study, start_date, end_date
            )  # type: ignore[call-arg]


class TestTailoredExperienceEntry:
    def test_minimal_valid(self) -> None:
        e = TailoredExperienceEntry(
            company="Acme",
            role="Engineer",
            start_date="2020",
            end_date="Present",
            bullets=["Built systems"],
        )
        assert e.company == "Acme"

    def test_missing_required_raises(self) -> None:
        with pytest.raises(ValidationError):
            TailoredExperienceEntry(
                company="Acme",
                role="Engineer",
                start_date="2020",
                end_date="Present",
            )  # type: ignore[call-arg]


class TestParsedResume:
    def test_minimal_valid(self) -> None:
        pr = ParsedResume(
            contact=ContactInfo(name="Test"),
            professional_summary="Summary",
            experience=[],
            skills=[],
            education=[],
        )
        assert pr.contact.name == "Test"
        assert pr.totals_yoe == 0

    def test_with_full_data(self, sample_parsed_resume: ParsedResume) -> None:
        pr = sample_parsed_resume
        assert pr.contact.email == "alice@example.com"
        assert len(pr.experience) == 1
        assert len(pr.skills) == 6
        assert len(pr.education) == 1
        assert pr.totals_yoe == 5

    def test_missing_required_raises(self) -> None:
        with pytest.raises(ValidationError):
            ParsedResume()  # type: ignore[call-arg]


class TestTailoredResume:
    def _minimal_tailored(self, **overrides) -> TailoredResume:
        """Helper: create a minimal valid TailoredResume with optional overrides."""
        base = dict(
            contact=ContactInfo(name="Test"),
            professional_summary="Summary",
            experience=[
                TailoredExperienceEntry(
                    company="Acme",
                    role="Engineer",
                    start_date="2020",
                    end_date="Present",
                    bullets=["Built systems"],
                ),
            ],
            skills=["Python"],
            education=[
                EducationEntry(
                    institution="Uni",
                    degree="BS",
                    field_of_study="CS",
                    start_date="2016",
                    end_date="2020",
                ),
            ],
            company="Acme",
            job_title="Engineer",
            confidence_score=70,
            ats_keyword_coverage=["python"],
            tailoring_notes="Notes",
        )
        base.update(overrides)
        return TailoredResume(**base)

    def test_minimal_valid(self) -> None:
        tr = self._minimal_tailored()
        assert tr.company == "Acme"
        assert tr.confidence_score == 70

    def test_output_filename(self) -> None:
        tr = self._minimal_tailored(
            company="CloudScale Inc",
            job_title="Senior Platform Engineer",
        )
        assert (
            tr.output_filename()
            == "resume_CloudScale_Inc_Senior_Platform_Engineer.docx"
        )

    def test_output_filename_special_chars(self) -> None:
        tr = self._minimal_tailored(
            company="A&B Co.",
            job_title="Sr. Dev (ML/AI)",
        )
        assert "resume_A_B_Co__Sr__Dev__ML_AI_.docx" == tr.output_filename()

    def test_confidence_score_bounds(self) -> None:
        for score in [0, 50, 100]:
            tr = self._minimal_tailored(confidence_score=score)
            assert tr.confidence_score == score

    def test_missing_required_raises(self) -> None:
        with pytest.raises(ValidationError):
            TailoredResume(
                contact=ContactInfo(name="Test"),
                professional_summary="Sum",
                experience=[],
                skills=[],
                education=[],
            )  # type: ignore[call-arg]


class TestPublicationEntry:
    def test_minimal_valid(self) -> None:
        p = PublicationEntry(
            title="Deep Learning Advances",
            venue="NeurIPS 2023",
            date="Dec 2023",
        )
        assert p.title == "Deep Learning Advances"
        assert p.publisher == ""
        assert p.link == ""

    def test_all_fields(self) -> None:
        p = PublicationEntry(
            title="Attention Is All You Need",
            venue="NeurIPS 2017",
            date="Jun 2017",
            publisher="Curran Associates",
            link="https://arxiv.org/abs/1706.03762",
        )
        assert p.publisher == "Curran Associates"
        assert "arxiv" in p.link

    def test_missing_required_raises(self) -> None:
        with pytest.raises(ValidationError):
            PublicationEntry(venue="Journal")  # type: ignore[call-arg]


class TestWorkshopEntry:
    def test_minimal_valid(self) -> None:
        w = WorkshopEntry(
            title="MLOps Best Practices",
            date="Mar 2023",
            place="Milan, Italy",
        )
        assert w.title == "MLOps Best Practices"

    def test_missing_required_raises(self) -> None:
        with pytest.raises(ValidationError):
            WorkshopEntry(title="Workshop", date="2023")  # type: ignore[call-arg]


class TestAwardEntry:
    def test_minimal_valid(self) -> None:
        a = AwardEntry(
            title="Best Paper Award",
            organization="IEEE",
            date="Dec 2022",
        )
        assert a.title == "Best Paper Award"

    def test_missing_required_raises(self) -> None:
        with pytest.raises(ValidationError):
            AwardEntry(title="Award", organization="Org")  # type: ignore[call-arg]


class TestInternationalExperienceEntry:
    def test_minimal_valid(self) -> None:
        e = InternationalExperienceEntry(
            place="Tokyo, Japan",
            date="Sep 2021 – Jun 2022",
            description="Exchange semester at University of Tokyo",
        )
        assert e.place == "Tokyo, Japan"

    def test_missing_required_raises(self) -> None:
        with pytest.raises(ValidationError):
            InternationalExperienceEntry(place="London")  # type: ignore[call-arg]


class TestParsedResumeNewFields:
    def test_new_fields_default_empty(self) -> None:
        pr = ParsedResume(
            contact=ContactInfo(name="Test"),
            professional_summary="Summary",
            experience=[],
            skills=[],
            education=[],
        )
        assert pr.publications == []
        assert pr.workshops == []
        assert pr.awards == []
        assert pr.international_experiences == []

    def test_new_fields_populated(self) -> None:
        pr = ParsedResume(
            contact=ContactInfo(name="Test"),
            professional_summary="Summary",
            experience=[],
            skills=[],
            education=[],
            publications=[
                PublicationEntry(
                    title="Test Paper",
                    venue="ICML 2023",
                    date="Jul 2023",
                )
            ],
            awards=[
                AwardEntry(
                    title="Dean's List",
                    organization="University",
                    date="2020",
                )
            ],
        )
        assert len(pr.publications) == 1
        assert len(pr.awards) == 1


class TestTailoredResumeNewFields:
    def _minimal_tailored(self, **overrides) -> TailoredResume:
        base = dict(
            contact=ContactInfo(name="Test"),
            professional_summary="Summary",
            experience=[
                TailoredExperienceEntry(
                    company="Acme",
                    role="Engineer",
                    start_date="2020",
                    end_date="Present",
                    bullets=["Built systems"],
                ),
            ],
            skills=["Python"],
            education=[
                EducationEntry(
                    institution="Uni",
                    degree="BS",
                    field_of_study="CS",
                    start_date="2016",
                    end_date="2020",
                ),
            ],
            company="Acme",
            job_title="Engineer",
            confidence_score=70,
            ats_keyword_coverage=["python"],
            tailoring_notes="Notes",
        )
        base.update(overrides)
        return TailoredResume(**base)

    def test_new_fields_default_empty(self) -> None:
        tr = self._minimal_tailored()
        assert tr.publications == []
        assert tr.workshops == []
        assert tr.awards == []
        assert tr.international_experiences == []

    def test_new_fields_populated(self) -> None:
        tr = self._minimal_tailored(
            publications=[
                PublicationEntry(
                    title="ML Research",
                    venue="ICML",
                    date="2023",
                )
            ],
            workshops=[
                WorkshopEntry(
                    title="Kubernetes Workshop",
                    date="2022",
                    place="Berlin",
                )
            ],
            awards=[
                AwardEntry(
                    title="Innovation Award",
                    organization="ACM",
                    date="2021",
                )
            ],
            international_experiences=[
                InternationalExperienceEntry(
                    place="Paris, France",
                    date="2020",
                    description="Research internship at INRIA",
                )
            ],
        )
        assert len(tr.publications) == 1
        assert len(tr.workshops) == 1
        assert len(tr.awards) == 1
        assert len(tr.international_experiences) == 1
