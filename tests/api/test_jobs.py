"""Tests for job queue endpoints."""


class TestQueueJob:
    async def test_queues_job_from_url(self, client, auth_headers):
        """POST with a URL returns 202 and a task_id."""
        r = await client.post("/api/v1/sessions", headers=auth_headers)
        sid = r.json()["session_id"]

        r = await client.post(
            f"/api/v1/sessions/{sid}/jobs",
            headers=auth_headers,
            data={"url": "https://example.com/jobs/123"},
        )
        assert r.status_code == 202
        assert "task_id" in r.json()

    async def test_queues_job_from_text(self, client, auth_headers):
        """POST with raw text returns 202 and a task_id."""
        r = await client.post("/api/v1/sessions", headers=auth_headers)
        sid = r.json()["session_id"]

        r = await client.post(
            f"/api/v1/sessions/{sid}/jobs",
            headers=auth_headers,
            data={"text": "Senior Engineer at TechCo — Go, cloud"},
        )
        assert r.status_code == 202

    async def test_requires_source(self, client, auth_headers):
        """POST without url/text/file returns 400."""
        r = await client.post("/api/v1/sessions", headers=auth_headers)
        sid = r.json()["session_id"]

        r = await client.post(
            f"/api/v1/sessions/{sid}/jobs",
            headers=auth_headers,
        )
        assert r.status_code == 400


class TestListJobs:
    async def test_lists_queued_jobs(self, client, auth_headers, store, sample_job):
        r = await client.post("/api/v1/sessions", headers=auth_headers)
        sid = r.json()["session_id"]

        state = await store.get("test-user", sid)
        state.parsed_job_postings.append(sample_job)
        await store.save("test-user", sid, state)

        r = await client.get(f"/api/v1/sessions/{sid}/jobs", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["job_title"] == "Senior Backend Engineer"


class TestRemoveJob:
    async def test_removes_job_by_index(self, client, auth_headers, store, sample_job):
        r = await client.post("/api/v1/sessions", headers=auth_headers)
        sid = r.json()["session_id"]

        state = await store.get("test-user", sid)
        state.parsed_job_postings.append(sample_job)
        await store.save("test-user", sid, state)

        r = await client.delete(f"/api/v1/sessions/{sid}/jobs/0", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["deleted"] is True
