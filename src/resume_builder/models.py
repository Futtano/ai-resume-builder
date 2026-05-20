"""
This module groups together Pydantic interfaces for communications
between agents
"""

from pydantic import BaseModel, Field, field_validator
from pathlib import Path
# ------------------------------------------------------------
# Shared primitives
# ------------------------------------------------------------


# ParsedResume - output of the resume analysis task
class ContactInfo(BaseModel):
    """Structured contact details"""

    name: str = Field(description="Full name of the candidate")
    email: str = Field(default="", description="Email address")
    phone: str = Field(default="", description="Phone number")
    location: str = Field(default="", description="City, country or region")
    linkedin: str = Field(default="", description="LinkedIn profile URL")
    github: str = Field(default="", description="GitHub profile URL")
    portfolio: str = Field(default="", description="Personal website or portfolio URL")


class ExperienceEntry(BaseModel):
    """Single work experience item"""

    company: str = Field(description="Company or organization name")
    role: str = Field(description="Job title or role")
    start_date: str = Field(description="Start date, e.g. Jan 2021 or 2021")
    end_date: str = Field(description="End date, e.g. Jan 2021 or 2021")
    location: str = Field(default="", description="Job location")
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
    degree_mark: str = Field(default="", description="Final degree mark")
    honours: str = Field(default="", description="Honours")


class PublicationEntry(BaseModel):
    """Single academic/scientific publication"""

    title: str = Field(description="Title of the publication")
    venue: str = Field(description="Conference, journal, or publisher name")
    date: str = Field(description="Publication date, e.g. Mar 2023 or 2023")
    publisher: str = Field(default="", description="Publisher or organization")
    link: str = Field(default="", description="URL or DOI link to the publication")


class WorkshopEntry(BaseModel):
    """Single workshop participation"""

    title: str = Field(description="Title of the workshop")
    date: str = Field(description="Workshop date, e.g. Jun 2022 or 2022")
    place: str = Field(
        description="Location or institution where the workshop was held"
    )


class AwardEntry(BaseModel):
    """Single award or recognition"""

    title: str = Field(description="Title of the award or recognition")
    organization: str = Field(
        description="Organization or institution that granted the award"
    )
    date: str = Field(description="Date the award was received, e.g. Dec 2021 or 2021")


class InternationalExperienceEntry(BaseModel):
    """Single international experience (study abroad, work exchange, etc.)"""

    place: str = Field(description="Country, city, or institution abroad")
    date: str = Field(
        description="Date or period of the experience, e.g. Sep 2020 – Jun 2021"
    )
    description: str = Field(description="Brief description of the experience")


# ------------------------------------------------------------
# Stage 1 output: parsed resume
# ------------------------------------------------------------


class ParsedResume(BaseModel):
    """
    Structured representation of the candidate's original resume
    Produced once by the ResumeAnalyzer agent and reused for every job
    """

    contact: ContactInfo = Field(description="Candidate's contact information")
    professional_summary: str = Field(
        default="",
        description="Original, verbatim or lightly cleaned professional summary of the candidate",
    )
    experience: list[ExperienceEntry] = Field(
        description="Work experience entries in reverse chronological order"
    )
    skills: list[str] = Field(description="All skills mentioned in the original resume")
    education: list[EducationEntry] = Field(
        description="Diplomas, degrees mentioned in the original resume"
    )
    certifications: list[str] = Field(
        default_factory=list, description="List of all certifications"
    )
    totals_yoe: int = Field(
        default=0, description="Estimated total years of professional experience"
    )
    projects: list["ProjectEntry"] = Field(
        default_factory=list,
        description="GitHub projects parsed from the candidate's repositories",
    )
    publications: list["PublicationEntry"] = Field(
        default_factory=list,
        description="Academic or scientific publications",
    )
    workshops: list["WorkshopEntry"] = Field(
        default_factory=list,
        description="Workshop participations",
    )
    awards: list["AwardEntry"] = Field(
        default_factory=list,
        description="Awards and recognitions",
    )
    international_experiences: list["InternationalExperienceEntry"] = Field(
        default_factory=list,
        description="International experiences (study abroad, work exchanges, etc.)",
    )


# ------------------------------------------------------------
# GitHub project info (populated by the project scraper + parser agent)
# ------------------------------------------------------------


class ProjectEntry(BaseModel):
    """
    Structured representation of a GitHub project.
    Produced by the project parser agent from raw GithubSearchTool output.
    """

    repo_name: str = Field(description="GitHub repository name, e.g. 'owner/repo'")
    repo_url: str = Field(description="Full URL to the GitHub repository")
    description: str = Field(
        description="Short but comprehensive description of what the project does"
    )
    tech_stack: list[str] = Field(
        description="Technologies, languages, and frameworks used"
    )
    architecture: str = Field(
        description=(
            "High-level explanation of how the project works: "
            "information flow, how components interact, system design"
        )
    )
    stars: int = Field(
        default=0,
        description="GitHub stars count",
    )


class Projects(BaseModel):
    """Structured representation of a list of ProjectEntry objects"""

    projects: list[ProjectEntry] = Field(
        default_factory=list, description="A list of GitHub projects"
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
    industry: str = Field(default="", description="Industry sector")
    team_size: str = Field(default="", description="Team or company size if mentioned")
    remote_policy: str = Field(
        default="", description="e.g. 'Remote', 'Hybrid', 'On-site'"
    )
    # raw_posting: str = Field(description="Full raw text of the job posting")


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
    location: str = Field(default="", description="Job location")
    bullets: list[str] = Field(
        description=(
            "3-6 rewritten achievement-oriented bullet points. "
            "Each starts with a strong action verb "
            "Quantify impact where data exist in the original"
        )
    )

    # @field_validator("bullets")
    # @classmethod
    # def at_least_two_bullets(cls, v: list[str]) -> list[str]:
    #     if len(v) < 2:
    #         raise ValueError(
    #             "Each experience entry must have at least two bullet points"
    #         )
    #     return v


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
    certifications: list[str] = Field(
        default_factory=list, description="List of all certifications"
    )
    projects: list[ProjectEntry] = Field(
        default_factory=list,
        description="GitHub projects selected for the tailored resume",
    )
    publications: list[PublicationEntry] = Field(
        default_factory=list,
        description="Publications selected for the tailored resume",
    )
    workshops: list[WorkshopEntry] = Field(
        default_factory=list,
        description="Workshop participations selected for the tailored resume",
    )
    awards: list[AwardEntry] = Field(
        default_factory=list,
        description="Awards and recognitions selected for the tailored resume",
    )
    international_experiences: list[InternationalExperienceEntry] = Field(
        default_factory=list,
        description="International experiences selected for the tailored resume",
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


class Improvements(BaseModel):
    """Improvements to be addressed to produce a better tailored resume"""

    quality: str | None = Field(
        description="Suggestion to improve the overall content quality of the resume."
    )
    ats_optimisation: str | None = Field(
        description="Suggestion to optimize the resume for ATS systems"
    )
    accuracy: str | None = Field(
        description="Suggestion to eliminate or modify exaggerated or fabricated claims"
    )
    consistency: str | None = Field(
        description="Suggestions about overall consistency, such as formatting, style, duplicates etc."
    )
    others: str | None = Field(description="Other improvement suggestions")


class ImprovedResume(BaseModel):
    """Composition of TailoredResume and potential improvements to be addressed"""

    current_resume: TailoredResume = Field(
        description="TailoredResume object produced by the resume writer"
    )
    improvements: Improvements | None = Field(
        description="Improvements to be made to the current_resume"
    )


# ------------------------------------------------------------
# Flow-level state
# ------------------------------------------------------------


class ResumeBuilderState(BaseModel):
    """
    Shared state for the ResumeBuilderFlow.
    Populated inrementally as the flow progresses.
    """

    session_id: str = Field(default="", description="Unique identifier for this run")
    resume_path: Path | None = Field(
        default=None, description="Absolute path to the resume file"
    )
    intro_brief: str = Field(default="", description="Brief professional introduction")
    job_files: list[Path] = Field(
        default_factory=list, description="Local .txt file paths for job postings"
    )
    job_urls: list[str] = Field(
        default_factory=list, description="Job posting URLs to scrape"
    )
    projects: list[str] = Field(
        default_factory=list,
        description="GitHub repository identifiers in owner/repo format",
    )

    # Populated during execution
    parsed_resume: ParsedResume | None = Field(
        default=None, description="Structured model of the old resume"
    )
    parsed_projects: list[ProjectEntry] = Field(
        default_factory=list,
        description="Structured project entries from GitHub repos",
    )
    parsed_job_postings: list[JobRequirements] = Field(
        default_factory=list,
        description="List of JobRequirements models for job postings",
    )
    tailored_resumes: list[TailoredResume] = Field(
        default_factory=list,
        description="List of structured models for each of the tailored resumes",
    )

    # Progress tracking (used by web interface)
    total_jobs: int = 0
    completed_jobs: int = 0
    errors: list[str] = Field(default_factory=list)
