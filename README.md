# Resume Builder

An AI-powered system designed to automatically tailor professional resumes to specific job descriptions. Built with CrewAI, Typer, and Pydantic.

This application uses a multi-agent AI system to analyze job requirements, identify relevant candidate skills, and rewrite resume content to maximize impact and ATS optimization.

## Features

- Multi-Agent Orchestration: Employs a specialized crew of agents (Job Analyzer, Resume Strategist, Resume Writer, and Quality Reviewer) for high-quality results.
- Flexible Job Inputs: Support for local text files, directories of files, or direct URLs via web scraping.
- GitHub Integration: Automatically scrapes and parses GitHub repositories to include technical projects in the tailored resume.
- ATS Optimization: Identifies and incorporates high-value keywords from job descriptions.
- Confidence Scoring: Provides a fit score and detailed tailoring notes for each generated resume.
- Professional Output: Generates clean, ready-to-use .docx files.
- Visual CLI: A robust terminal interface with progress tracking and result summaries.

## Installation

This project uses uv for dependency management.

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd resume_builder
   ```

2. Install dependencies:

   ```bash
   # Using crewAI (recommended)
   crewai install

   # Or using uv directly
   uv sync
   ```

## Configuration

Create a .env file in the root directory with your API keys and settings:

```env
OPENAI_API_KEY=your_openai_api_key_here
# Optional: Override default models
WRITER_MODEL=gpt-4o
ANALYST_MODEL=gpt-4o-mini
```

## Usage

The project provides a CLI utility named resume-builder.

### Basic Usage

Tailor a resume for a single job posting file:

```bash
resume-builder run \
    --resume inputs/my_resume.pdf \
    --jobs inputs/jobs/software_engineer.txt \
    --intro "I am a backend engineer with 5 years of experience."
```

### Advanced Usage

Include GitHub projects and scrape job postings from the web:

```bash
resume-builder run \
    --resume inputs/my_resume.pdf \
    --job-urls "https://example.com/careers/devops-role" \
    --github-urls "https://github.com/youruser/awesome-project" \
    --output-dir ./tailored_resumes
```

### CLI Options

- -r, --resume: Path to your original resume (PDF).
- -j, --jobs: One or more paths to job posting .txt files.
- --jobs-dir: Directory containing multiple job posting files.
- --job-urls: One or more URLs to scrape job descriptions from.
- --github-urls: GitHub repository URLs to include as projects.
- -i, --intro: A brief note about yourself to guide the AI.
- -o, --output-dir: Directory to save generated .docx files (default: ./outputs).

## How It Works

The system follows a structured CrewAI Flow:

1. Resume Extraction: Extracts text from the provided PDF.
2. Structured Parsing: Converts raw text into a structured data model.
3. Project Enrichment: (Optional) Scrapes provided GitHub repositories for technical details.
4. Tailoring Crew: Launches a 4-agent crew for each job posting:
    - Job Analyzer: Extracts mandatory skills and ATS keywords.
    - Resume Strategist: Determines the narrative angle for the application.
    - Resume Writer: Rewrites experience bullets and the professional summary.
    - Quality Reviewer: Validates output against the original resume to ensure accuracy.
5. Document Export: Formats the final data into a professional Word document.

## Testing

Run the test suite using pytest:

```bash
pytest
```
