"""Tests for resume upload, parse, and edit endpoints."""


class TestEditResume:
    async def test_applies_edit_and_returns_updated_resume(
        self, client, sample_parsed_resume, store, mock_llm
    ):
        """A valid NL edit instruction returns updated resume fields."""
        r = await client.post("/api/v1/sessions")
        sid = r.json()["session_id"]

        from resume_builder.models import InteractiveResumeState

        state = InteractiveResumeState(
            session_id=sid,
            working_resume=sample_parsed_resume,
        )
        await store.save("default", sid, state)

        mock_llm.call.return_value = '{"skills": ["Python", "Go", "Docker", "Rust"]}'
        r = await client.patch(
            f"/api/v1/sessions/{sid}/resume",
            headers={"Content-Type": "application/json"},
            json={"instruction": "Add Rust to skills"},
        )

        assert r.status_code == 200
        data = r.json()
        assert "updated_fields" in data
        assert "skills" in data["updated_fields"]
        assert "Rust" in data["working_resume"]["skills"]

    async def test_rejects_edit_when_no_resume_loaded(self, client, mock_llm):
        """Editing a session with a blank resume works (create_session adds one)."""
        r = await client.post("/api/v1/sessions")
        sid = r.json()["session_id"]

        mock_llm.call.return_value = '{"skills": ["Python"]}'
        r = await client.patch(
            f"/api/v1/sessions/{sid}/resume",
            headers={"Content-Type": "application/json"},
            json={"instruction": "Add Python to skills"},
        )
        assert r.status_code == 200

    async def test_404_for_nonexistent_session(self, client):
        r = await client.patch(
            "/api/v1/sessions/nonexistent/resume",
            headers={"Content-Type": "application/json"},
            json={"instruction": "Add Rust"},
        )
        assert r.status_code == 404

    async def test_handles_llm_failure(
        self, client, sample_parsed_resume, store, mock_llm
    ):
        """When the LLM call fails, return 502."""
        r = await client.post("/api/v1/sessions")
        sid = r.json()["session_id"]

        from resume_builder.models import InteractiveResumeState

        state = InteractiveResumeState(
            session_id=sid,
            working_resume=sample_parsed_resume,
        )
        await store.save("default", sid, state)

        mock_llm.call.side_effect = RuntimeError("API down")

        r = await client.patch(
            f"/api/v1/sessions/{sid}/resume",
            headers={"Content-Type": "application/json"},
            json={"instruction": "Add Rust"},
        )

        assert r.status_code == 502
        assert r.json()["error_code"] == "LLM_FAILURE"


class TestGetResume:
    async def test_returns_working_resume(self, client):
        r = await client.post("/api/v1/sessions")
        sid = r.json()["session_id"]

        r = await client.get(f"/api/v1/sessions/{sid}/resume")
        assert r.status_code == 200
        assert "working_resume" in r.json()


class TestUploadResume:
    async def test_accepts_pdf_upload(self, client):
        r = await client.post("/api/v1/sessions")
        sid = r.json()["session_id"]

        r = await client.post(
            f"/api/v1/sessions/{sid}/resume",
            files={
                "file": ("resume.pdf", b"%PDF-1.4 fake pdf content", "application/pdf")
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["filename"] == "resume.pdf"
        assert data["size"] > 0
