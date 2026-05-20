# SPEC: Replace Processors with Agent Tools

## Context

The current pipeline does data extraction in two phases: first, Processor classes (`JobProcessor`, `ProjectProcessor`, `ResumeProcessor`) scrape/read external data in `main.py` *before* the Flow kicks off; then the raw strings are passed to CrewAI agents for LLM parsing. The `ResumeParsingCrew` already moved away from this pattern — its agent uses `ExtractResumeContentTool` (a `BaseTool` wrapping `pymupdf4llm`) to extract PDF text directly. This spec extends that same pattern to job posting extraction and GitHub repo extraction, then deletes all Processor classes.

## Design Decisions

| Decision | Choice |
|---|---|
| URL scraping | Wrap `crawl4ai` library in a `BaseTool` |
| File reading for jobs | Reuse existing `crewai_tools.FileReadTool` |
| GitHub tools | Two tools: `GitHubListDirTool` + `GitHubFileReadTool` |
| State: `projects_raw` | Remove it. Pass repo identifiers directly to crew |
| State: job sources | Separate fields: `job_files: list[Path]` + `job_urls: list[str]` |
| Error handling in tools | Return `"[ERROR] ..."` strings (not raise) |
| Directory expansion | Flow/main.py expands `--jobs-dir` into individual `Path`s |
| GitHub repo format | Require `owner/repo`. `main.py` normalizes full URLs |
| Processors | Delete all three: `JobProcessor`, `ProjectProcessor`, `ResumeProcessor` |
| `kickoff_for_each` input | `dict(source=..., source_type='file'\|'url')` (jobs) or `dict(source=..., source_type='github_repo')` (projects) |
| Testing | Mock at HTTP level (e.g., `responses` library) |

## Files to Delete

- `src/resume_builder/processors/job.py`
- `src/resume_builder/processors/project.py`
- `src/resume_builder/processors/resume.py`
- `src/resume_builder/processors/__init__.py`

## New Files

### `src/resume_builder/crews/job_parsing_crew/tools.py`

**`JobURLScrapeTool`** — scrapes a job posting URL using `crawl4ai`.

```
Name:       job_url_scrape
Input:      url: str
Output:     scraped markdown string, or "[ERROR] <reason>" on failure
Internals:  Wraps crawl4ai's AsyncWebCrawler + BrowserConfig/CrawlerRunConfig.
            Same config as current JobProcessor: headless=True, magic=True,
            remove_overlay_elements=True, excluded_tags=["nav","footer","header","aside","script","style"],
            CacheMode.BYPASS.
            Uses asyncio.run() to bridge async -> sync (matching current pattern).
            Prefers fit_markdown, falls back to raw_markdown -> extracted_content.
```

Tool provided to the `job_parser` agent alongside `FileReadTool`.

### `src/resume_builder/crews/repo_parsing_crew/tools.py`

**`GitHubListDirTool`** — lists directory contents of a GitHub repo.

```
Name:       github_list_dir
Input:      repo: str (format: "owner/repo")
            path: str = "" (optional subdirectory)
Output:     formatted list of {name, type, path} entries, or "[ERROR] <reason>"
Internals:  GET https://api.github.com/repos/{repo}/contents/{path}
            Headers: Accept: application/vnd.github+json, Authorization: Bearer {settings.gh_token}
            Returns one line per entry: "[dir] path/" or "[file] path (N bytes)"
```

**`GitHubFileReadTool`** — fetches and decodes a single file from a GitHub repo.

```
Name:       github_file_read
Input:      repo: str (format: "owner/repo")
            file_path: str (e.g., "README.md", "src/main.py")
Output:     decoded file content as string, or "[ERROR] <reason>"
Internals:  GET https://api.github.com/repos/{repo}/contents/{file_path}
            Same auth headers as ListDirTool.
            Base64-decodes response["content"].
```

Both tools provided to the `repo_parser` agent.

## State Model Changes (`models.py`)

```python
# REMOVE:
job_postings_raw: list[str]  # pre-extracted text
projects_raw: list[str]      # pre-scraped markdown

# ADD:
job_files: list[Path] = Field(default_factory=list)   # local .txt file paths
job_urls: list[str] = Field(default_factory=list)     # job posting URLs

# KEEP (already exists):
projects: list[str]  # GitHub repo identifiers (owner/repo)
resume_path: Path | None
```

## Flow Changes (`flow.py`)

### Constructor

```python
def __init__(
    self,
    resume_path: Path,
    job_files: list[Path] | None = None,
    job_urls: list[str] | None = None,
    projects: list[str] | None = None,
    intro_brief: str = "",
    output_dir: Path | None = None,
    on_progress: Callable[[str, int, int], None] | None = None,
) -> None:
```

State fields set from constructor: `state.job_files`, `state.job_urls`, `state.projects`.

Validation: at least one of `job_files` or `job_urls` must be non-empty.

### `parse_jobs_step` — rewritten

Merge `job_files` and `job_urls` into a single input list for `kickoff_for_each`:

```python
inputs = []
for f in self.state.job_files:
    inputs.append({"source": str(f), "source_type": "file"})
for u in self.state.job_urls:
    inputs.append({"source": u, "source_type": "url"})

job_postings = (
    JobParsingCrew()
    .crew()
    .kickoff_for_each(inputs=inputs)
)
```

### `parse_projects_step` — rewritten

Pass repo identifiers with `github_repo` source type:

```python
projects = (
    RepoParsingCrew()
    .crew()
    .kickoff_for_each(
        inputs=[
            {"source": repo, "source_type": "github_repo"}
            for repo in self.state.projects
        ]
    )
)
```

No changes to `parse_resume_step`, `generate_tailored_resume`, or `export_documents`.

## Task YAML Changes

### `job_parsing_crew/config/tasks.yaml`

Template variables: `{job_posting_raw}` -> `{source}` + `{source_type}`.

Task description instructs the agent:
- If `source_type == "file"`: use `FileReadTool` to read the local file
- If `source_type == "url"`: use `job_url_scrape` tool to scrape the URL
- Then parse the resulting text into a `JobRequirements` model

### `repo_parsing_crew/config/tasks.yaml`

Template variables: `{project_raw}` -> `{source}` + `{source_type}`.

Task description instructs the agent:
- Use `github_list_dir` to explore the repo structure
- Use `github_file_read` to fetch key files (README.md, pyproject.toml, etc.)
- Build a `ProjectEntry` model from the fetched content
- Never fabricate information not present in the fetched files

### No changes needed
- Both `agents.yaml` files
- Both `llm.yaml` files

## Agent Tool Assignments (`crew.py` changes)

### `JobParsingCrew`

```python
from resume_builder.crews.job_parsing_crew.tools import JobURLScrapeTool
from crewai_tools import FileReadTool

@agent
def job_parser(self) -> Agent:
    return Agent(
        config=self.agents_config["job_parser"],
        verbose=settings.crewai_verbose,
        tools=[FileReadTool(), JobURLScrapeTool()],
    )
```

### `RepoParsingCrew`

```python
from resume_builder.crews.repo_parsing_crew.tools import (
    GitHubListDirTool,
    GitHubFileReadTool,
)

@agent
def repo_parser(self) -> Agent:
    return Agent(
        config=self.agents_config["repo_parser"],
        verbose=settings.crewai_verbose,
        tools=[GitHubListDirTool(), GitHubFileReadTool()],
    )
```

## `main.py` Changes

### Remove
- Imports of `JobProcessor`, `ProjectProcessor`
- The entire "Extraction Phase" block (`console.status(...)` with `JobProcessor`/`ProjectProcessor`)

### Add
- Expand `--jobs-dir` into a list of `Path`s (glob `*.txt`)
- Collect `--job-files` as `list[Path]`
- Collect `--job-urls` as `list[str]`
- Normalize `--projects` GitHub URLs to `owner/repo` format (strip `https://github.com/`, trailing slashes)
- Pass `job_files`, `job_urls`, `projects` to `ResumeBuilderFlow`

### Validation
- At least one of `--job-files`, `--jobs-dir`, or `--job-urls` must be provided

## Crew Smoke-test Blocks

Each crew's `__main__` block used for standalone testing currently relies on Processors:

- **`job_parsing_crew/crew.py`**: Load `.txt` files directly with `pathlib`, pass with `source_type="file"` to `kickoff_for_each`.
- **`repo_parsing_crew/crew.py`**: Pass repo identifiers with `source_type="github_repo"` to `kickoff_for_each`.

## Testing

- Use `responses` library to mock HTTP calls at the network level
- `JobURLScrapeTool`: mock `crawl4ai.AsyncWebCrawler.arun` to return synthetic `CrawlResult`
- `GitHubListDirTool` / `GitHubFileReadTool`: use `responses` to mock `api.github.com` calls
- Existing tests in `tests/` need flow constructor calls updated (new parameter names)
- Known broken tests in `tests/test_flow.py` (reference `resume_raw_text` param that no longer exists) should be fixed

## Verification

1. `uv run resume-builder run inputs/my_resume.pdf --job-files inputs/sample_job.txt -i "brief intro"` — single file-based job
2. `uv run resume-builder run inputs/my_resume.pdf --jobs-dir inputs/ -i "brief intro"` — directory of job files
3. `uv run resume-builder run inputs/my_resume.pdf -j "https://example.com/job-posting" -i "brief intro"` — URL-based job
4. `uv run resume-builder run inputs/my_resume.pdf --job-files inputs/sample_job.txt -p "owner/repo1" -p "owner/repo2" -i "brief intro"` — jobs + GitHub projects
5. `pytest` — all tests pass
6. `ruff check src/ tests/` — no lint errors
