"""
test_job_scraper.py
-------------------
Tests for the job_scraper module with mocked crawl4ai.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from resume_builder.tools.job_scraper import scrape_job_url


class TestJobScraper:
    def _make_mock_crawler(self, result: MagicMock) -> AsyncMock:
        """Build a properly async-mocked AsyncWebCrawler."""
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value.arun = AsyncMock(return_value=result)
        mock_cm.__aexit__.return_value = None
        return mock_cm

    def test_successful_scrape(self) -> None:
        """Test successful scraping with mock crawl4ai."""
        mock_result = MagicMock()
        mock_result.success = True

        mock_markdown = MagicMock()
        mock_markdown.fit_markdown = "# Job Title\nCompany XYZ is hiring..."
        mock_markdown.raw_markdown = "# Job Title\nCompany XYZ is hiring..."
        mock_result.markdown = mock_markdown
        mock_result.extracted_content = None

        mock_crawler = self._make_mock_crawler(mock_result)

        with patch("resume_builder.tools.job_scraper.AsyncWebCrawler", return_value=mock_crawler):
            text = scrape_job_url("https://example.com/job")

        assert "Job Title" in text
        assert "Company XYZ" in text

    def test_scrape_failure_raises(self) -> None:
        """Test that a failed crawl raises RuntimeError."""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "Connection refused"

        mock_crawler = self._make_mock_crawler(mock_result)

        with patch("resume_builder.tools.job_scraper.AsyncWebCrawler", return_value=mock_crawler):
            with pytest.raises(RuntimeError, match="Failed to crawl"):
                scrape_job_url("https://example.com/bad")

    def test_empty_content_raises(self) -> None:
        """Test that empty content raises RuntimeError."""
        mock_result = MagicMock()
        mock_result.success = True

        mock_markdown = MagicMock()
        mock_markdown.fit_markdown = None
        mock_markdown.raw_markdown = None
        mock_result.markdown = mock_markdown
        mock_result.extracted_content = None

        mock_crawler = self._make_mock_crawler(mock_result)

        with patch("resume_builder.tools.job_scraper.AsyncWebCrawler", return_value=mock_crawler):
            with pytest.raises(RuntimeError, match="No extractable content"):
                scrape_job_url("https://example.com/empty")

    def test_falls_back_to_raw_markdown(self) -> None:
        """Test fallback to raw_markdown when fit_markdown is None."""
        mock_result = MagicMock()
        mock_result.success = True

        mock_markdown = MagicMock()
        mock_markdown.fit_markdown = None
        mock_markdown.raw_markdown = "## Senior Engineer\nApply now!"
        mock_result.markdown = mock_markdown
        mock_result.extracted_content = None

        mock_crawler = self._make_mock_crawler(mock_result)

        with patch("resume_builder.tools.job_scraper.AsyncWebCrawler", return_value=mock_crawler):
            text = scrape_job_url("https://example.com/job")

        assert "Senior Engineer" in text
