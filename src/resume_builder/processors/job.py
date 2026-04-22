"""
job.py
------
Processor for extracting job posting text from files and URLs.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

from resume_builder.logger import get_logger

logger = get_logger(__name__)


class JobProcessor:
    """
    Handles the extraction of job posting text from files, directories, and URLs.
    """

    def __init__(self) -> None:
        self._extracted: list[str] = []

    @property
    def extracted(self) -> list[str]:
        """List of extracted job posting texts."""
        return self._extracted

    def from_file(self, path: Path) -> JobProcessor:
        """Load job posting from a text file."""
        try:
            text = path.read_text(encoding="utf-8")
            self._extracted.append(text)
            logger.debug("Loaded job posting: %s (%d chars)", path.name, len(text))
        except Exception as exc:
            logger.warning("Could not read %s: %s", path, exc)
        return self

    def from_directory(self, dir_path: Path) -> JobProcessor:
        """Load all .txt job postings from a directory."""
        if not dir_path.exists() or not dir_path.is_dir():
            logger.warning("Directory not found or not a directory: %s", dir_path)
            return self

        for job_file in sorted(dir_path.glob("*.txt")):
            self.from_file(job_file)
        return self

    def from_url(self, url: str) -> JobProcessor:
        """Scrape job posting from a URL."""
        logger.info("Scraping job posting: %s", url)
        try:
            text = self._scrape_url(url)
            self._extracted.append(text)
            logger.info("Scraped %d chars from %s", len(text), url)
        except Exception as exc:
            logger.warning("Could not scrape %s: %s", url, exc)
        return self

    def _scrape_url(self, url: str) -> str:
        """Internal helper for scraping a single URL."""
        browser_cfg = BrowserConfig(headless=True, verbose=False)
        run_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            excluded_tags=["nav", "footer", "header", "aside", "script", "style"],
            magic=True,
            remove_overlay_elements=True,
        )

        async def _run() -> str:
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                result = await crawler.arun(url=url, config=run_cfg)

            if not result.success:
                raise RuntimeError(
                    f"Failed to crawl {url}: {result.error_message or 'unknown error'}"
                )

            fit_md = result.markdown.fit_markdown
            raw_md = result.markdown.raw_markdown
            text = fit_md or raw_md or result.extracted_content or ""
            if not text.strip():
                raise RuntimeError(f"No extractable content found at {url}")

            return text

        return asyncio.run(_run())
