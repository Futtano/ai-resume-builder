"""
main.py
-------
CLI entry point for the application.
"""

from __future__ import annotations
import os
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

# Load .env before any imports that read env vars
load_dotenv()

from resume_builder.flow import ResumeBuilderFlow  # noqa: E402
from resume_builder.logger import configure_logging, get_logger  # noqa: E402
from resume_builder.tools.job_scraper import scrape_job_url  # noqa: E402

logger = get_logger(__name__)

app = typer.Typer(
    name="resume-builder",
    help="AI-powered resume tailoring - one tailored resume per job posting.",
    add_completion=False,
)
console = Console()


@app.command("run")
def run(
    resume: Path = typer.Option(
        ...,
        "--resume",
        "-r",
        help="Path to your resume PDF",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    jobs: list[Path] | None = typer.Option(
        None,
        "--jobs",
        "-j",
        help="One or more job posting .txt files",
    ),
    jobs_dir: Path | None = typer.Option(
        None,
        "--jobs-dir",
        help="Directory of job posting files (alternative to --jobs)",
        exists=True,
    ),
    job_urls: list[str] | None = typer.Option(
        None,
        "--job-urls",
        help="One or more job posting URLs to scrape",
    ),
    github_repos: list[str] | None = typer.Option(
        None,
        "--github-repos",
        help="One or more GitHub repository URLs to include as projects",
    ),
    intro: str = typer.Option(
        "",
        "--intro",
        "-i",
        help="Brief introductory note about yourself / what you're looking for",
    ),
    output_dir: Path = typer.Option(
        Path("./outputs"),
        "--output-dir",
        "-o",
        help="Directory to write tailored resume .docx files",
    ),
) -> None:
    """Generate tailored resumes for each job posting."""
    configure_logging()
    logger.info("=== Resume Builder CLI started ===")

    # -- Validate inputs----------------------------------------------
    job_posting_files: list[Path] = []

    if jobs:
        job_posting_files.extend(jobs)
    if jobs_dir:
        job_posting_files.extend(sorted(jobs_dir.glob("*.txt")))

    if not job_posting_files and not job_urls:
        logger.error("No job postings provided")
        console.print(
            "[red]Error:[/] Provide job postings via --jobs, --jobs-dir, or --job-urls"
        )
        raise typer.Exit(1)

    # Validate API key present
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        logger.error("No API key found in environment")
        console.print(
            "[red]Error:[/] No API key found. "
            "Set OPENAI_API_KEY or ANTHROPIC_API_KEY in your .env file."
        )
        raise typer.Exit(1)

    # -- Load job posting texts ----------------------------------------------
    job_postings: list[str] = []
    for job_file in job_posting_files:
        try:
            text = job_file.read_text(encoding="utf-8")
            job_postings.append(text)
            logger.debug("Loaded job posting: %s (%d chars)", job_file.name, len(text))
        except Exception as exc:
            logger.warning("Could not read %s: %s", job_file, exc)
            console.print(f"[yellow]Warning:[/] Could not read {job_file}: {exc}")

    # -- Scrape job posting URLs ------------------------------------------
    if job_urls:
        for url in job_urls:
            try:
                console.print(f"[dim]Scraping {url}...[/]")
                logger.info("Scraping URL: %s", url)
                text = scrape_job_url(url)
                job_postings.append(text)
                console.print(f"[green]✓[/] Scraped {len(text):,} chars from {url}")
            except Exception as exc:
                logger.warning("Could not scrape %s: %s", url, exc)
                console.print(f"[yellow]Warning:[/] Could not scrape {url}: {exc}")

    if not job_postings:
        logger.error("All job posting sources failed to load")
        console.print("[red]Error:[/] All job posting files failed to load.")
        raise typer.Exit(1)

    logger.info("Loaded %d job posting(s) total", len(job_postings))

    # -- Banner ----------------------------------------------
    file_count = len(job_postings) - (len(job_urls) if job_urls else 0)
    url_count = len(job_urls) if job_urls else 0
    sources = []
    if file_count:
        sources.append(f"{file_count} file(s)")
    if url_count:
        sources.append(f"{url_count} URL(s)")

    console.print(
        Panel(
            f"[bold]Resume:[/] {resume.name}\n"
            f"[bold]Job postings:[/] {len(job_postings)} ({', '.join(sources)})\n"
            f"[bold]Output:[/] {output_dir}",
            title="[bold blue]Resume Builder[/]",
            expand=False,
        )
    )

    # -- Run the flow ----------------------------------------------
    completed_count = 0
    errors: list[str] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description][task.description]"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("Starting...", total=None)

        def on_progress(message: str, _completed: int, _total: int) -> None:
            nonlocal completed_count
            completed_count = completed_count
            progress.update(task_id, description=message)

        flow = ResumeBuilderFlow(
            resume_pdf_path=resume,
            job_postings=job_postings,
            intro_brief=intro,
            output_dir=output_dir,
            on_progress=on_progress,
            github_repos=github_repos,
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
