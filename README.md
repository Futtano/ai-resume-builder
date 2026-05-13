# Resume Builder

An AI-powered system that automatically tailors professional resumes to specific job postings. Built with CrewAI, Typer, and Pydantic.

## Features

* **Multi-Agent Orchestration**: Four specialized agents (Job Analyzer, Resume Strategist, Resume Writer, Quality Reviewer) collaborate on each resume.
* **Flexible Job Inputs**: Support for local text files, directories, or direct URLs via web scraping.
* **GitHub Integration**: Scrapes and parses GitHub repositories to include technical projects.
* **ATS Optimization**: Identifies and incorporates high-value keywords from job descriptions.
* **Confidence Scoring**: Provides a fit score and tailoring notes for each generated resume.
* **Professional Output**: Generates ready-to-use .docx files.
* **Visual CLI**: Terminal interface with progress tracking and result summaries.

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# Clone and enter the repository
git clone https://github.com/Futtano/ai-resume-builder
cd resume\_builder

# Install dependencies
uv sync
```

## Configuration

Create a `.env` file in the project root. Put your API keys (OPENAI\_API\_KEY, GROQ\_API\_KEY, HF\_TOKEN, ANTHROPIC\_API\_KEY, etc.) here. Use GH\_TOKEN for GitHub project-parsing functionalities. Custom API endpoints for LLMs must be specified in the `llm.yaml` config files (via the `base\_url` parameter).

## Usage

### Basic Usage

```bash
resume-builder run inputs/my\_resume.pdf --job-files inputs/jobs/software\_engineer.txt --intro "I am a backend engineer with 5 years of experience."
```

### Advanced Usage

```bash
resume-builder run inputs/my\_resume.pdf \\
  --job-urls "https://example.com/careers/devops-role" \\
  --projects "https://github.com/youruser/awesome-project" \\
  --output-dir ./tailored\_resumes
```

### CLI Options

|Option|Description|
|-|-|
|`resume` (positional)|Path to your resume (PDF or text)|
|`--job-files`, `--jobs-dir`|Job posting files or directory|
|`-j, --job-urls`|URLs to scrape job postings from|
|`-p, --projects`|GitHub repository URLs to include as projects|
|`-i, --intro`|Brief note about yourself to guide the AI|
|`-o, --output-dir`|Output directory (default: `./outputs`)|

## Architecture

The system uses a CrewAI Flow with the following pipeline:

1. **Resume Extraction**: Extracts text from the PDF
2. **Structured Parsing**: Converts raw text into a structured data model
3. **Job Parsing**: Parses job postings into requirements
4. **Project Enrichment** (optional): Scrapes GitHub repositories for project details
5. **Tailoring Crew**: Runs a 4-agent crew for each job posting:

   * Job Analyzer: Extracts mandatory skills and ATS keywords
   * Resume Strategist: Determines the narrative angle
   * Resume Writer: Rewrites experience and summary
   * Quality Reviewer: Validates output against the original
6. **Document Export**: Formats results into Word documents

## Testing

```bash
pytest
```

## Linting

```bash
ruff check src/ tests/
ruff format src/ tests/
```

## Project Structure

```
src/resume\_builder/
├── main.py              # CLI entry point
├── flow.py              # ResumeBuilderFlow orchestrator
├── models.py            # Pydantic data models
├── settings.py          # Configuration
├── processors/         # Resume, job, and project processors
└── crews/               # CrewAI crews and their configs
    ├── resume\_parsing\_crew/
    ├── resume\_building\_crew/
    ├── job\_parsing\_crew/
    └── repo\_parsing\_crew/
```

