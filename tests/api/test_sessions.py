"""Tests for session CRUD endpoints."""


class TestCreateSession:
    async def test_creates_session_and_returns_201(self, client):
        response = await client.post("/api/v1/sessions")
        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) == 32  # UUID hex
        assert data["state"]["session_id"] == data["session_id"]
        assert data["state"]["working_resume"] is not None


class TestGetSession:
    async def test_returns_session_if_exists(self, client):
        # Create first
        r = await client.post("/api/v1/sessions")
        sid = r.json()["session_id"]

        # Then get
        r = await client.get(f"/api/v1/sessions/{sid}")
        assert r.status_code == 200
        assert r.json()["session_id"] == sid

    async def test_returns_404_for_unknown_session(self, client):
        r = await client.get("/api/v1/sessions/nonexistent")
        assert r.status_code == 404
        assert r.json()["error_code"] == "SESSION_NOT_FOUND"


class TestListSessions:
    async def test_returns_paginated_list(self, client):
        # Create 3 sessions
        for _ in range(3):
            await client.post("/api/v1/sessions")

        r = await client.get("/api/v1/sessions?limit=2&offset=0")
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3


class TestDeleteSession:
    async def test_deletes_session(self, client):
        r = await client.post("/api/v1/sessions")
        sid = r.json()["session_id"]

        r = await client.delete(f"/api/v1/sessions/{sid}")
        assert r.status_code == 200
        assert r.json()["deleted"] is True

        # Gone
        r = await client.get(f"/api/v1/sessions/{sid}")
        assert r.status_code == 404

    async def test_delete_nonexistent_returns_false(self, client):
        r = await client.delete("/api/v1/sessions/nope")
        assert r.status_code == 200
        assert r.json()["deleted"] is False
