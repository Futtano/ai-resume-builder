"""
This module groups together Pydantic interfaces for communications
between agents
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator

# ------------------------------------------------------------
# Shared primitives
# ------------------------------------------------------------


# ParsedResume - output of the resume analysis task
class ContactInfo(BaseModel):
    """Structured contact details"""

    name: str = Field(description="Full name of the candidate")
    email: Optional[str] = Field(default=None, description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    location: Optional[str] = Field(default=None, description="City, country or region")
    linkedin: Optional[str] = Field(default=None, description="LinkedIn profile URL")
    github: Optional[str] = Field(default=None, description="GitHub profile URL")
    portfolio: Optional[str] = Field(
        default=None, description="Personal website or portfolio URL"
    )


class ExperienceEntry(BaseModel):
    """Single work experience item"""

    company: str = Field(description="Company or organization name")
    role: str = Field(description="Job title or role")
    start_date: str = Field(description="Start date, e.g. Jan 2021 or 2021")
    end_date: str = Field(description="End date, e.g. Jan 2021 or 2021")
    location: Optional[str] = Field(default=None, description="Job location")
    bullets: list[str] = Field(
        description="Bullet points describing responsibilities and achievements"
    )
    skills_demonstrated: list[str] = Field(
        default_factory=list,
        description="Technical or soft skills evident from this role",
    )


class EducationEntry(BaseModel):
    """Single education item"""

    institution: str = Field(description="School, university etc.")
    degree: str = Field(description="Diploma, bachelor, master etc.")
    field_of_study: str = Field(description="Field of study")
    start_date: str = Field(description="Start date, e.g. Jan 2021 or 2021")
    end_date: str = Field(description="Start date, e.g. Jan 2021 or 2021")
    degree_mark: Optional[str] = Field(default=None, description="Final degree mark")
    honours: Optional[bool] = Field(default=None, description="Honours")


# ------------------------------------------------------------
# Stage 1 output: parsed resume
# ------------------------------------------------------------


class ParsedResume(BaseModel):
    """
    Structured representation of the candidate's original resume
    Produced once by the ResumeAnalyzer agent and reused for every job
    """

    contact: ContactInfo = Field(description="Candidate's contact information")
    professional_summary: Optional[str] = Field(
        default=None,
        description="Original, verbatim or lightly cleaned professional summary of the candidate",
    )
    experience: list[ExperienceEntry] = Field(
        description="Work experience entries in reverse chronological order"
    )
    skills: list[str] = Field(description="All skills mentioned in the original resume")
    education: list[EducationEntry] = Field(
        description="Diplomas, degrees mentioned in the original resume"
    )
    certifications: Optional[list[str]] = Field(
        default=None, description="List of all certifications"
    )
    raw_text: str = Field(
        description="Full raw text of the old resume, preserved as a reference"
    )  # always put this as a fallback
    totals_yoe: Optional[int] = Field(
        default=None, description="Estimated total years of professional experience"
    )


# ------------------------------------------------------------
# Stage 2 output: job requirements
# ------------------------------------------------------------


# JobRequirements - output of the job analysis task
class JobRequirements(BaseModel):
    """
    Structured analysis of a single job posting
    Produced by the JobAnalyzer agent for each job
    """

    job_title: str = Field(description="Job title or role as written in the posting")
    company: str = Field(description="Company name")
    seniority_level: str = Field(
        description="e.g. Junior, Mid-Level, Senior, Lead, Principal"
    )
    required_skills: list[str] = Field(
        description="Skills explicitly marked as required or mandatory"
    )
    preferred_skills: list[str] = Field(
        description="Skills marked as nice-to-have, preferred or bonus"
    )
    key_responsibilities: list[str] = Field(
        description="The main responsibilities or duties of the role"
    )
    ats_keywords: list[str] = Field(
        description=(
            "High-value keywords and phrases to include for ATS optimization. "
            "Exact strings from the posting."
        )
    )
    industry: Optional[str] = Field(default=None, description="Industry sector")
    team_size: Optional[str] = Field(
        default=None, description="Team or company size if mentioned"
    )
    remote_policy: Optional[str] = Field(
        default=None, description="e.g. 'Remote', 'Hybrid', 'On-site'"
    )
    raw_posting: str = Field(description="Full raw text of the job posting")


# ------------------------------------------------------------
# Stage 3 output: tailoring strategy
# ------------------------------------------------------------


# TailoringStrategy - output of strategist
class TailoringStrategy(BaseModel):
    """
    Strategic plan for tailoring the resume to a specific job.
    Produced by ResumeStrategist and consumed by ResumeWriter
    """

    match_score: int = Field(
        ge=0,
        le=100,
        description="Estimated profile-to-job fit score before tailoring (0-100)",
    )
    skills_to_emphasize: list[str] = Field(
        description="Skills the candidate has that are directly relevant - lead with these"
    )
    skills_to_deprioritise: list[str] = Field(
        description="Skills the candidate have that are NOT relevant to this job"
    )
    experience_bullets_to_rewrite: list[str] = Field(
        description=(
            "Specific existing bullet points to rewrite for better alignment. "
            "List the original text."
        )
    )
    summary_angle: str = Field(
        description=(
            "The narrative angle for the professional summary. "
            "e.g. 'Lead with cloud infrastructure experience, position as DevOps specialist "
            "transitioning from backend engineering'"
        )
    )
    keywords_to_weave_in: list[str] = Field(
        description="ATS keywords that must appear naturally in the final resume"
    )
    gaps_and_mitigations: str = Field(
        description=(
            "Skills or experience the candidate lacks, and how to honestly address "
            "each gap. (e.g. 'No Kubernetes experience - mention Docker expertise and "
            "willingness to learn"
        )
    )
    honest_constraints: str = Field(
        description=(
            "Hard constraints: things the writer must NOT fabricate or exaggerate. "
            "Grounded in the candidate's actual experience"
        )
    )


# ------------------------------------------------------------
# Stage 4 output: tailored experience entry
# ------------------------------------------------------------


class TailoredExperienceEntry(BaseModel):
    """A rewritten experience entry, optimised for the target job."""

    company: str = Field(description="Company or organization name")
    role: str = Field(description="Job title or role")
    start_date: str = Field(description="Start date, e.g. Jan 2021 or 2021")
    end_date: str = Field(description="End date, e.g. Jan 2021 or 2021")
    location: Optional[str] = Field(default=None, description="Job location")
    bullets: list[str] = Field(
        description=(
            "3-6 rewritten achievement-oriented bullet points. "
            "Each starts with a strong action verb "
            "Quantify impact where data exist in the original"
        )
    )

    @field_validator("bullets")
    @classmethod
    def at_least_two_bullets(cls, v: list[str]) -> list[str]:
        if len(v) < 2:
            raise ValueError(
                "Each experience entry must have at least two bullet points"
            )
        return v


# ------------------------------------------------------------
# Stage 5 output: final tailored resume
# ------------------------------------------------------------


class TailoredResume(BaseModel):
    """
    The complete, job-tailored resume.
    Final output of the full pipeline for a single job posting
    """

    # Metadata (not shown on resume, used for file naming + UI)
    job_title: str = Field(description="Job title or role as written in the posting")
    company: str = Field(description="Company name")
    session_id: int = Field(description="Session identifier")

    # Resume content
    contact: ContactInfo = Field(description="Candidate's contact information")
    professional_summary: str = Field(
        description=(
            "3-5 sentence professional summary tailored to this specific role. "
            "Opens with the candidate's most relevant identity for this job. "
            "Incorporates key ATS terms naturally"
        )
    )
    experience: list[TailoredExperienceEntry] = Field(
        description="Rewritten work experience, same entries as original but reorder if needed"
    )
    skills: list[str] = Field(
        description=(
            "Curated skill list: relevant skills first, grouped logically. Max 20 items"
        )
    )
    education: list[EducationEntry] = Field(
        description="Diplomas, degrees mentioned in the original resume"
    )
    certifications: Optional[list[str]] = Field(
        default=None, description="List of all certifications"
    )

    # Quality metadata (not shown on resume)
    ats_keyword_coverage: list[str] = Field(
        description="ATS keywords from the job posting that appear in the resume"
    )

    missing_keywords: list[str] = Field(
        default_factory=list,
        description="ATS keywords that could not be included without fabrication",
    )

    tailoring_notes: str = Field(
        description=(
            "Human-readable explanation of the main tailoring decisions made. "
            "Useful for the candidate to understand what changed and why."
        )
    )

    confidence_score: int = Field(
        ge=0,
        le=100,
        description=(
            "Writer's estimated fit score after tailoring. "
            "Reflects how well the tailored resume matches the job requirements."
        ),
    )

    @field_validator("skills")
    @classmethod
    def cap_skills_at_twenty(cls, v: list[str]) -> list[str]:
        return v[:20]

    def output_filename(self) -> str:
        """Generate a clean filename for this resume"""
        safe_company = "".join(c if c.isalnum() else "_" for c in self.company)
        safe_title = "".join(c if c.isalnum() else "_" for c in self.job_title)
        return f"resume_{safe_company}_{safe_title}.docx"


# ------------------------------------------------------------
# Flow-level state
# ------------------------------------------------------------


class ResumeBuilderState(BaseModel):
    """
    Shared state for the ResumeBuilderFlow.
    Populated inrementally as the flow progresses.
    """

    session_id: str = Field(default="", description="Unique identifier for this run")
    resume_raw_text: str = Field(
        default="", description="Raw text extracted from the PDF"
    )
    into_brief: str = Field(default="", description="Raw text for each job posting")
    job_posting_raw: list[str] = Field(
        default_factory=list, description="Raw text of each job posting"
    )

    # Populated during execution
    parsed_resume: Optional[ParsedResume] = Field(
        default=None, description="Structured model of the old resume"
    )
    tailored_resume: Optional[list[TailoredResume]] = Field(
        default_factory=list,
        description="List of structured models for each of the tailored resumes",
    )

    # Progress tracking (used by web interface)
    total_jobs: int = 0
    completed_jobs: int = 0
    errors: list[str] = Field(default_factory=list)
