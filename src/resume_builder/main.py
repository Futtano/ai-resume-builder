"""
main.py
-------
CLI entry point for the application.
"""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from resume_builder.flow import ResumeBuilderFlow
from resume_builder.logger import configure_logging, get_logger

logger = get_logger(__name__)

app = typer.Typer(
    name="resume-builder",
    help="AI-powered resume tailoring - one tailored resume per job posting.",
    add_completion=False,
)

console = Console()


def _normalize_github_repo(raw: str) -> str:
    """Convert a GitHub URL to owner/repo format."""
    repo = raw.strip().rstrip("/")
    repo = repo.removeprefix("https://")
    repo = repo.removeprefix("http://")
    repo = repo.removeprefix("www.")
    repo = repo.removeprefix("github.com/")
    return repo


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
    job_files: Annotated[
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
            help="Directory of job posting files (alternative to --job-files)",
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
            help="One or more GitHub repos (owner/repo format or full URL) to include as projects",
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

    # -- Collect job sources ----------------------------------------------
    job_files_list = list(job_files or [])
    if jobs_dir:
        job_files_list.extend(sorted(jobs_dir.glob("*.txt")))

    job_urls_list = list(job_urls or [])

    if not job_files_list and not job_urls_list:
        logger.error("No job postings provided")
        console.print(
            "[red]Error:[/] No job postings provided. "
            "Use --job-files, --jobs-dir, or --job-urls."
        )
        raise typer.Exit(1)

    # -- Normalize projects ----------------------------------------------
    projects_list = [_normalize_github_repo(p) for p in (projects or [])]

    # -- Summary ----------------------------------------------
    console.print(
        Panel(
            f"[bold]Resume:[/] {resume.name}\n"
            f"[bold]Job sources:[/] {len(job_files_list)} file(s), {len(job_urls_list)} URL(s)\n"
            f"[bold]Projects:[/] {len(projects_list)} GitHub repo(s)\n"
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
            resume_path=resume.absolute(),
            job_files=job_files_list,
            job_urls=job_urls_list,
            projects=projects_list,
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
        len(job_files_list) + len(job_urls_list),
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
        f"\n[green]✓ Done.[/] {len(resumes)}/{len(job_files_list) + len(job_urls_list)} resumes written to [bold]{output_dir}[/]\n"
    )


if __name__ == "__main__":
    app()
