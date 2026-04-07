"""
main.py
-------
CLI entry point for the Resume Builder.

Usage:
    # Basic - resume PDF + one or more job posting files
    resume-builder run \\
        --resume inputs/my_resume.pdf \\
        --jobs inputs/job1.txt inputs/job2.txt \\
        --intro "I am a backend engineer looking to move \\
            into platform engineering"

    # With a directory of job posting
    resume-builder run \\
        --resume inputs/my_resume.pdf \\
        --jobs-dir inputs/jobs/ \\
        --intro "..."

    # Verbose mode (show agent thinking)
    CREWAI_VERBOSE=true resume-builder run ...
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

# Load .env before any imports that read env vars
load_dotenv()

from resume_builder.flow import ResumeBuilderFlow  # noqa: E402

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
    jobs: Optional[list[Path]] = typer.Option(
        None,
        "--jobs",
        "-j",
        help="One or more job posting .txt files",
    ),
    jobs_dir: Optional[Path] = typer.Option(
        None,
        "--jobs-dir",
        help="Directory of .txt job posting files (alternative to --jobs)",
        exists=True,
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

    # -- Validate inputs----------------------------------------------
    job_posting_files: list[Path] = []

    if jobs:
        job_posting_files.extend(jobs)
    if jobs_dir:
        job_posting_files.extend(sorted(jobs_dir.glob("*.txt")))

    if not job_posting_files:
        console.print("[red]Error:[/] Provide job postings via --jobs or --jobs-dir")
        raise typer.Exit(1)

    # Validate API key present
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        console.print(
            "[red]Error:[/] No API key found. "
            "Set OPENAI_API_KEY or ANTHROPIC_API_KEY in your .env file."
        )
        raise typer.Exit(1)

    # -- Load job posting texts ----------------------------------------------
    job_postings: list[str] = []
    for job_file in job_posting_files:
        try:
            job_postings.append(job_file.read_text(encoding="utf-8"))
        except Exception as exc:
            console.print(f"[yellow]Warning:[/] Could not read {job_file}: {exc}")

    if not job_postings:
        console.print("[red]Error:[/] All job posting files failed to load.")
        raise typer.Exit(1)

    # -- Banner ----------------------------------------------
    console.print(
        Panel(
            f"[bold]Resume:[/] {resume.name}\n"
            f"[bold]Job postings:[/] {len(job_postings)}\n"
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
        )

        try:
            flow.kickoff()
            errors = flow.state.errors
        except Exception as exc:
            console.print(f"\n[red]Fatal error:[/] {exc}")
            raise typer.Exit(1)

    # -- Results summary ----------------------------------------------
    console.print()
    resumes = flow.state.tailored_resumes

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
        console.print(f"\n[yellow]⚠ {len(errors)} job(s) failed:[/]")
        for err in errors:
            console.print(f"  • {err}")

    console.print(
        f"\n[green]✓ Done.[/] {len(resumes)}/{len(job_postings)} resumes written to [bold]{output_dir}[/]\n"
    )


if __name__ == "__main__":
    app()
