# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run the pipeline (resume is positional arg, at least one job source required)
uv run resume-builder run inputs/my_resume.pdf --job-files inputs/sample_job.txt -i "brief intro"

# Visualize the Flow as a Mermaid diagram
uv run plot

# Run all tests
pytest
# Run a single test file
pytest tests/test_models.py

# Lint and format
ruff check src/ tests/
ruff format src/ tests/
```

## Architecture

This is a CrewAI-based resume tailoring tool. The architecture follows a **Flow + Crew hybrid** pattern:

- **`ResumeBuilderFlow`** (`flow.py`) is the top-level orchestrator — a CrewAI `Flow` subclass that manages the pipeline via `@start()` and `@listen()` decorators.
- **Each pipeline stage delegates to a Crew** (single-agent or multi-agent CrewAI crew). Crews live in `src/resume_builder/crews/<name>_crew/` with `crew.py` + `config/{agents,tasks,llm}.yaml`.
- **State** is a Pydantic model `ResumeBuilderState` (`models.py`) passed through the Flow, populated incrementally.

### Pipeline stages

Three `@start()` methods run in parallel:

1. **`parse_resume_step`** — `ResumeParsingCrew` (single agent + `ExtractResumeContentTool` for PDF extraction via `pymupdf4llm`). Outputs `ParsedResume`.
2. **`parse_jobs_step`** — `JobParsingCrew` uses `kickoff_for_each` to process multiple job postings in parallel. Outputs `list[JobRequirements]`.
3. **`parse_projects_step`** — `RepoParsingCrew` uses `kickoff_for_each` to parse scraped GitHub repo data. Outputs `list[ProjectEntry]`.

Then `@listen(and_(parse_resume_step, parse_jobs_step, parse_projects_step))` triggers:

4. **`generate_tailored_resume`** — `ResumeBuilderCrew` (3 agents: strategist → writer → quality reviewer, sequential). Uses `kickoff_for_each` per job posting. Outputs `list[ImprovedResume]`.
5. **`export_documents`** — Renders `.docx` files via `formatter.py`.

### Data flow

PDF/text → raw string (processors) → Pydantic models (crews) → `.docx` (formatter).

Processors (`src/resume_builder/processors/`) handle non-LLM extraction: `ResumeProcessor` extracts text from PDFs, `JobProcessor` loads/scrapes job postings, `ProjectProcessor` hits the GitHub API for repo files. These run _before_ the Flow kicks off (in `main.py`).

### LLM configuration

Each crew defines its LLM config in a YAML file loaded manually via `@llm`-decorated methods. **The YAML structure differs between crews:**

- `resume_building_crew/config/llm.yaml` uses **named top-level keys** (`resume_strategist_llm`, `resume_writer_llm`, `quality_reviewer_llm`) — one per agent. The `@llm` methods index into these keys.
- All other crews (`resume_parsing`, `job_parsing`, `repo_parsing`) use a **flat structure** — the entire YAML document maps directly to `LLM(**kwargs)`.

All crews use `provider: openai` with a custom `base_url` (Lightning AI) and Google Gemini models. The `base_url` is set per-crew in YAML, not via environment variables.

### Docx output

- **`utils.py` (`render_resume`)** is what the Flow calls in `export_documents`. It uses `docxtpl` to fill `templates/resume_template.docx` with the `TailoredResume` model dict.
- `formatter.py` (`ResumeFormatter`) uses `python-docx` to programmatically build the document. It is currently unused by the Flow (only referenced in the `__main__` smoke-test block of `resume_building_crew/crew.py`).

### Key dependencies

- **CrewAI** with `litellm` extra — multi-agent orchestration
- **Typer** + **Rich** — CLI and terminal UI
- **Pydantic** — all data models and flow state
- **python-docx** — `.docx` generation
- **pymupdf4llm** — PDF text extraction (Markdown-aware)
- **crawl4ai** — job posting URL scraping

## Project conventions

- Environment variables go in `.env` (gitignored). API keys: `OPENAI_API_KEY`, `GH_TOKEN`, etc.
- Settings are centralized in `settings.py` via pydantic-settings. Import the `settings` singleton; never read `os.environ` directly.
- Logging is configured once in `main.py` via `configure_logging()`. All modules get loggers via `get_logger(__name__)` from `logger.py`. Logs write to `tmp/resume_builder.log` (rotating, 5MB max); console output only when `LOG_LEVEL=DEBUG`.
- Type hints use Python 3.10+ syntax (`list[str]`, `str | None`), not the old `Optional[str]`/`List[str]`.
- Tests use pytest with mocks for LLM calls. No real LLM or external services are called in tests. Shared fixtures in `tests/conftest.py`.

## Known issues

- Tests in `tests/test_flow.py` reference a `resume_raw_text` constructor parameter that no longer exists on `ResumeBuilderFlow` — the flow now takes `resume_path: Path`. These tests will fail and need updating.
