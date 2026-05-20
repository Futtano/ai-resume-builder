"""
job_parsing_crew/tools.py
-------------------------
Tools for extracting job posting text from URLs using crawl4ai.
"""

import asyncio

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class JobURLScrapeInput(BaseModel):
    url: str = Field(description="The URL of the job posting to scrape")


class JobURLScrapeTool(BaseTool):
    """Scrape a job posting URL using crawl4ai's headless browser."""

    name: str = "job_url_scrape"
    description: str = (
        "Scrape text content from a job posting URL. "
        "Use this when source_type is 'url' and a job posting URL is provided. "
        "Returns the scraped markdown text, or an error message string on failure."
    )
    args_schema: type[BaseModel] = JobURLScrapeInput

    def _run(self, url: str) -> str:
        browser_cfg = BrowserConfig(headless=True, verbose=False)
        run_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            excluded_tags=["nav", "footer", "header", "aside", "script", "style"],
            magic=True,
            remove_overlay_elements=True,
        )

        async def _scrape() -> str:
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                result = await crawler.arun(url=url, config=run_cfg)

            if not result.success:
                return (
                    f"[ERROR] Failed to crawl {url}: "
                    f"{result.error_message or 'unknown error'}"
                )

            text = (
                result.markdown.fit_markdown
                or result.markdown.raw_markdown
                or result.extracted_content
                or ""
            )
            if not text.strip():
                return f"[ERROR] No extractable content found at {url}"

            return text

        try:
            return asyncio.run(_scrape())
        except Exception as exc:
            return f"[ERROR] Failed to scrape {url}: {exc}"
