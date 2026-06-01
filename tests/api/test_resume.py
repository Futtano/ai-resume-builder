"""Tests for resume upload, parse, and edit endpoints."""

from unittest.mock import patch


class TestEditResume:
    async def test_applies_edit_and_returns_updated_resume(
        self, client, auth_headers, sample_parsed_resume, store
    ):
        """A valid NL edit instruction returns updated resume fields."""
        r = await client.post("/api/v1/sessions", headers=auth_headers)
        sid = r.json()["session_id"]

        from resume_builder.models import InteractiveResumeState

        state = InteractiveResumeState(
            session_id=sid,
            working_resume=sample_parsed_resume,
        )
        await store.save("test-user", sid, state)

        # Mock the LLM call at the crewai source
        with patch(
            "crewai.LLM.call",
            return_value='{"skills": ["Python", "Go", "Docker", "Rust"]}',
        ):
            r = await client.patch(
                f"/api/v1/sessions/{sid}/resume",
                headers={**auth_headers, "Content-Type": "application/json"},
                json={"instruction": "Add Rust to skills"},
            )

        assert r.status_code == 200
        data = r.json()
        assert "updated_fields" in data
        assert "skills" in data["updated_fields"]
        assert "Rust" in data["working_resume"]["skills"]

    async def test_rejects_edit_when_no_resume_loaded(self, client, auth_headers):
        """Editing a session with a blank resume works (create_session adds one)."""
        r = await client.post("/api/v1/sessions", headers=auth_headers)
        sid = r.json()["session_id"]

        with patch("crewai.LLM.call", return_value='{"skills": ["Python"]}'):
            r = await client.patch(
                f"/api/v1/sessions/{sid}/resume",
                headers={**auth_headers, "Content-Type": "application/json"},
                json={"instruction": "Add Python to skills"},
            )
        assert r.status_code == 200

    async def test_404_for_nonexistent_session(self, client, auth_headers):
        r = await client.patch(
            "/api/v1/sessions/nonexistent/resume",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={"instruction": "Add Rust"},
        )
        assert r.status_code == 404

    async def test_handles_llm_failure(
        self, client, auth_headers, sample_parsed_resume, store
    ):
        """When the LLM call fails, return 502."""
        r = await client.post("/api/v1/sessions", headers=auth_headers)
        sid = r.json()["session_id"]

        from resume_builder.models import InteractiveResumeState

        state = InteractiveResumeState(
            session_id=sid,
            working_resume=sample_parsed_resume,
        )
        await store.save("test-user", sid, state)

        from unittest.mock import MagicMock

        mock_llm_instance = MagicMock()
        mock_llm_instance.call.side_effect = RuntimeError("API down")

        with patch(
            "resume_builder.api.services.session_service.LLM",
            return_value=mock_llm_instance,
        ):
            r = await client.patch(
                f"/api/v1/sessions/{sid}/resume",
                headers={**auth_headers, "Content-Type": "application/json"},
                json={"instruction": "Add Rust"},
            )

        assert r.status_code == 502
        assert r.json()["error_code"] == "LLM_FAILURE"


class TestGetResume:
    async def test_returns_working_resume(self, client, auth_headers):
        r = await client.post("/api/v1/sessions", headers=auth_headers)
        sid = r.json()["session_id"]

        r = await client.get(f"/api/v1/sessions/{sid}/resume", headers=auth_headers)
        assert r.status_code == 200
        assert "working_resume" in r.json()


class TestUploadResume:
    async def test_accepts_pdf_upload(self, client, auth_headers):
        r = await client.post("/api/v1/sessions", headers=auth_headers)
        sid = r.json()["session_id"]

        r = await client.post(
            f"/api/v1/sessions/{sid}/resume",
            headers=auth_headers,
            files={
                "file": ("resume.pdf", b"%PDF-1.4 fake pdf content", "application/pdf")
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["filename"] == "resume.pdf"
        assert data["size"] > 0
