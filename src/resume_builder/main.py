"""
main.py
-------
CLI entry point for the application.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

# FIXME: Maybe find a way to load envs after the imports

# Load .env before any imports that read env vars
load_dotenv()

from resume_builder.flow import ResumeBuilderFlow  # noqa: E402
from resume_builder.logger import configure_logging, get_logger  # noqa: E402
from resume_builder.processors.job import JobProcessor
from resume_builder.processors.project import ProjectProcessor
from resume_builder.processors.resume import ResumeProcessor

logger = get_logger(__name__)


app = typer.Typer(
    name="resume-builder",
    help="AI-powered resume tailoring - one tailored resume per job posting.",
    add_completion=False,
)
console = Console()


@app.command("run")
def run(
    resume: Annotated[
        Path,
        typer.Argument(
            help="Path to your resume (PDF or text file)",
            exists=True,
            file_okay=True,
            dir_okay=False,
        ),
    ],
    jobs: Annotated[
        list[Path] | None,
        typer.Option(
            "--job-files",
            help="One or more job posting .txt files",
        ),
    ] = None,
    jobs_dir: Annotated[
        Path | None,
        typer.Option(
            "--jobs-dir",
            help="Directory of job posting files (alternative to --jobs)",
            exists=True,
        ),
    ] = None,
    job_urls: Annotated[
        list[str] | None,
        typer.Option(
            "-j",
            "--job-urls",
            help="One or more job posting URLs to scrape",
        ),
    ] = None,
    projects: Annotated[
        list[str] | None,
        typer.Option(
            "-p",
            "--projects",
            help="One or more GitHub repo URLs to include as projects",
        ),
    ] = None,
    intro: Annotated[
        str,
        typer.Option(
            "--intro",
            "-i",
            help="Brief introductory note about yourself / what you're looking for",
        ),
    ] = "",
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            "-o",
            help="Directory to write tailored resume .docx files",
        ),
    ] = Path("./outputs"),
) -> None:
    """Generate tailored resumes for each job posting."""
    configure_logging()
    logger.info("=== Resume Builder CLI started ===")

    # # -- Validate API keys ----------------------------------------------
    # if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
    #     logger.error("No API key found in environment")
    #     console.print(
    #         "[red]Error:[/] No API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env"
    #     )
    #     raise typer.Exit(1)

    # -- Extraction Phase ----------------------------------------------
    with console.status("[bold green]Extracting data...") as status:
        # 1. Resume
        try:
            status.update(f"[bold green]Extracting resume: {resume.name}...")
            resume_processor = ResumeProcessor().from_file(resume)
            resume_raw = resume_processor.extracted
        except Exception as exc:
            logger.error("Fatal resume extraction error: %s", exc)
            console.print(f"[red]Error:[/] Could not extract resume: {exc}")
            raise typer.Exit(1)

        # 2. Jobs
        job_processor = JobProcessor()
        if jobs:
            for jf in jobs:
                status.update(f"[bold green]Loading job file: {jf.name}...")
                job_processor.from_file(jf)
        if jobs_dir:
            status.update(f"[bold green]Loading jobs from directory: {jobs_dir}...")
            job_processor.from_directory(jobs_dir)
        if job_urls:
            for url in job_urls:
                status.update(f"[bold green]Scraping job URL: {url}...")
                job_processor.from_url(url)

        job_postings = job_processor.extracted
        if not job_postings:
            logger.error("No job postings extracted")
            console.print(
                "[red]Error:[/] No job postings provided or all failed to load."
            )
            raise typer.Exit(1)

        # 3. Projects
        projects_raw = []
        if projects:
            status.update(f"[bold green]Scraping {len(projects)} GitHub repo(s)...")
            project_processor = ProjectProcessor().from_github(projects)
            projects_raw = project_processor.extracted

    # -- Summary ----------------------------------------------
    console.print(
        Panel(
            f"[bold]Resume:[/] {resume.name} ({len(resume_raw):,} chars)\n"
            f"[bold]Job postings:[/] {len(job_postings)} source(s)\n"
            f"[bold]Projects:[/] {len(projects_raw)} GitHub repo(s)\n"
            f"[bold]Output:[/] {output_dir}",
            title="[bold blue]Resume Builder[/]",
            expand=False,
        )
    )

    # -- Run the flow ----------------------------------------------
    errors: list[str] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description][task.description]"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("Starting...", total=None)

        def on_progress(message: str, _completed: int, _total: int) -> None:
            progress.update(task_id, description=message)

        flow = ResumeBuilderFlow(
            resume_raw_text=resume_raw,
            job_postings_raw=job_postings,
            projects_raw=projects_raw,
            intro_brief=intro,
            output_dir=output_dir,
            on_progress=on_progress,
        )

        try:
            flow.kickoff()
            errors = flow.state.errors
        except Exception as exc:
            logger.error("Fatal flow error: %s", exc, exc_info=True)
            console.print(f"\n[red]Fatal error:[/] {exc}")
            raise typer.Exit(1)

    # -- Results summary ----------------------------------------------
    console.print()
    resumes = flow.state.tailored_resumes

    logger.info(
        "Flow complete: %d/%d resumes generated, %d errors",
        len(resumes),
        len(job_postings),
        len(errors),
    )

    if resumes:
        table = Table(
            title="Generated Resumes", show_header=True, header_style="bold blue"
        )
        table.add_column("Company", style="cyan")
        table.add_column("Role")
        table.add_column("Confidence", justify="center")
        table.add_column("File")

        for r in resumes:
            score_color = (
                "green"
                if r.confidence_score >= 70
                else "yellow"
                if r.confidence_score >= 50
                else "red"
            )
            table.add_row(
                r.company,
                r.job_title,
                f"[{score_color}]{r.confidence_score}%[/]",
                r.output_filename(),
            )

        console.print(table)

    if errors:
        logger.warning("%d job(s) had errors", len(errors))
        console.print(f"\n[yellow]⚠ {len(errors)} job(s) failed:[/]")
        for err in errors:
            console.print(f"  • {err}")

    logger.info("All done — %d resume(s) written to %s", len(resumes), output_dir)
    console.print(
        f"\n[green]✓ Done.[/] {len(resumes)}/{len(job_postings)} resumes written to [bold]{output_dir}[/]\n"
    )


if __name__ == "__main__":
    app()
