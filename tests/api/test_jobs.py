"""Tests for job queue endpoints."""


class TestQueueJob:
    async def test_queues_job_from_url(self, client):
        """POST with a URL returns 202 and a task_id."""
        r = await client.post("/api/v1/sessions")
        sid = r.json()["session_id"]

        r = await client.post(
            f"/api/v1/sessions/{sid}/jobs",
            json={"url": "https://example.com/jobs/123"},
        )
        assert r.status_code == 202
        assert "task_id" in r.json()

    async def test_queues_job_from_text(self, client):
        """POST with raw text returns 202 and a task_id."""
        r = await client.post("/api/v1/sessions")
        sid = r.json()["session_id"]

        r = await client.post(
            f"/api/v1/sessions/{sid}/jobs",
            json={"text": "Senior Engineer at TechCo — Go, cloud"},
        )
        assert r.status_code == 202

    async def test_requires_source(self, client):
        """POST without url/text returns 400."""
        r = await client.post("/api/v1/sessions")
        sid = r.json()["session_id"]

        r = await client.post(
            f"/api/v1/sessions/{sid}/jobs",
            json={},
        )
        assert r.status_code == 400


class TestListJobs:
    async def test_lists_queued_jobs(self, client, store, sample_job):
        r = await client.post("/api/v1/sessions")
        sid = r.json()["session_id"]

        state = await store.get("default", sid)
        state.parsed_job_postings.append(sample_job)
        await store.save("default", sid, state)

        r = await client.get(f"/api/v1/sessions/{sid}/jobs")
        assert r.status_code == 200
        data = r.json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["job_title"] == "Senior Backend Engineer"


class TestRemoveJob:
    async def test_removes_job_by_index(self, client, store, sample_job):
        r = await client.post("/api/v1/sessions")
        sid = r.json()["session_id"]

        state = await store.get("default", sid)
        state.parsed_job_postings.append(sample_job)
        await store.save("default", sid, state)

        r = await client.delete(f"/api/v1/sessions/{sid}/jobs/0")
        assert r.status_code == 200
        assert r.json()["deleted"] is True
