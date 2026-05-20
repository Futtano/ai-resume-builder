"""
test_job_url_scrape_tool.py
--------------------------
Tests for JobURLScrapeTool (crawl4ai-based URL scraping).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


from resume_builder.crews.job_parsing_crew.tools import JobURLScrapeTool


class TestJobURLScrapeTool:
    def test_tool_metadata(self) -> None:
        tool = JobURLScrapeTool()
        assert tool.name == "job_url_scrape"
        assert "source_type" in tool.description

    def test_scrape_success(self) -> None:
        result_mock = MagicMock()
        result_mock.success = True
        result_mock.markdown.fit_markdown = "# Job Posting\nWe are hiring..."
        result_mock.markdown.raw_markdown = "raw md"
        result_mock.extracted_content = ""

        crawler_mock = MagicMock()
        crawler_mock.arun = AsyncMock(return_value=result_mock)
        crawler_mock.__aenter__ = AsyncMock(return_value=crawler_mock)
        crawler_mock.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "resume_builder.crews.job_parsing_crew.tools.AsyncWebCrawler",
            return_value=crawler_mock,
        ):
            tool = JobURLScrapeTool()
            output = tool._run("https://example.com/job")

        assert output == "# Job Posting\nWe are hiring..."

    def test_scrape_fallback_to_raw_markdown(self) -> None:
        result_mock = MagicMock()
        result_mock.success = True
        result_mock.markdown.fit_markdown = ""
        result_mock.markdown.raw_markdown = "raw fallback content"
        result_mock.extracted_content = ""

        crawler_mock = MagicMock()
        crawler_mock.arun = AsyncMock(return_value=result_mock)
        crawler_mock.__aenter__ = AsyncMock(return_value=crawler_mock)
        crawler_mock.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "resume_builder.crews.job_parsing_crew.tools.AsyncWebCrawler",
            return_value=crawler_mock,
        ):
            tool = JobURLScrapeTool()
            output = tool._run("https://example.com/job")

        assert output == "raw fallback content"

    def test_scrape_failure(self) -> None:
        result_mock = MagicMock()
        result_mock.success = False
        result_mock.error_message = "Connection refused"

        crawler_mock = MagicMock()
        crawler_mock.arun = AsyncMock(return_value=result_mock)
        crawler_mock.__aenter__ = AsyncMock(return_value=crawler_mock)
        crawler_mock.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "resume_builder.crews.job_parsing_crew.tools.AsyncWebCrawler",
            return_value=crawler_mock,
        ):
            tool = JobURLScrapeTool()
            output = tool._run("https://fail.example.com")

        assert output.startswith("[ERROR]")
        assert "Connection refused" in output

    def test_scrape_exception(self) -> None:
        with patch(
            "resume_builder.crews.job_parsing_crew.tools.AsyncWebCrawler",
            side_effect=RuntimeError("Network error"),
        ):
            tool = JobURLScrapeTool()
            output = tool._run("https://bad.example.com")

        assert output.startswith("[ERROR]")
        assert "Network error" in output

    def test_scrape_empty_content(self) -> None:
        result_mock = MagicMock()
        result_mock.success = True
        result_mock.markdown.fit_markdown = ""
        result_mock.markdown.raw_markdown = ""
        result_mock.extracted_content = ""

        crawler_mock = MagicMock()
        crawler_mock.arun = AsyncMock(return_value=result_mock)
        crawler_mock.__aenter__ = AsyncMock(return_value=crawler_mock)
        crawler_mock.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "resume_builder.crews.job_parsing_crew.tools.AsyncWebCrawler",
            return_value=crawler_mock,
        ):
            tool = JobURLScrapeTool()
            output = tool._run("https://empty.example.com")

        assert output.startswith("[ERROR]")
        assert "No extractable content" in output
