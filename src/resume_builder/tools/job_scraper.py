"""
job_scraper.py
--------------
Job posting scraper using crawl4ai for JS-rendered pages.

Uses a headless Chromium browser to fully render pages
(including React/Vue hydration) and extract clean markdown.
"""

from __future__ import annotations

import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


def scrape_job_url(url: str) -> str:
    """
    Fetch a job posting URL and return clean markdown text.

    Uses crawl4ai (headless Chromium) so JavaScript-heavy pages
    render and hydrate before extraction.

    Returns the extracted text, or raises RuntimeError on failure.
    """
    browser_cfg = BrowserConfig(
        headless=True,
        verbose=False,
    )
    run_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        excluded_tags=["nav", "footer", "header", "aside", "script", "style"],
        # Auto-dismiss overlays, cookie banners, popups
        magic=True,
        remove_overlay_elements=True,
    )

    async def _run() -> str:
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)

        if not result.success:  # type: ignore[reportAttributeAccessIssue]
            raise RuntimeError(
                f"Failed to crawl {url}: {result.error_message or 'unknown error'}"  # type: ignore[reportAttributeAccessIssue]
            )

        # Prefer fit_markdown (main content only), fall back to raw markdown
        fit_md = result.markdown.fit_markdown  # type: ignore[reportAttributeAccessIssue]
        raw_md = result.markdown.raw_markdown  # type: ignore[reportAttributeAccessIssue]
        text = fit_md or raw_md or result.extracted_content or ""  # type: ignore[reportAttributeAccessIssue]
        if not text.strip():
            raise RuntimeError(f"No extractable content found at {url}")

        return text

    return asyncio.run(_run())
