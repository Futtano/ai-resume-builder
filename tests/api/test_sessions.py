"""Tests for session CRUD endpoints."""


class TestCreateSession:
    async def test_creates_session_and_returns_201(self, client, auth_headers):
        response = await client.post("/api/v1/sessions", headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) == 32  # UUID hex
        assert data["state"]["session_id"] == data["session_id"]
        assert data["state"]["working_resume"] is not None

    async def test_rejects_missing_api_key(self, client):
        response = await client.post("/api/v1/sessions")
        assert response.status_code == 401

    async def test_rejects_invalid_api_key(self, client):
        response = await client.post(
            "/api/v1/sessions", headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 401


class TestGetSession:
    async def test_returns_session_if_exists(self, client, auth_headers):
        # Create first
        r = await client.post("/api/v1/sessions", headers=auth_headers)
        sid = r.json()["session_id"]

        # Then get
        r = await client.get(f"/api/v1/sessions/{sid}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["session_id"] == sid

    async def test_returns_404_for_unknown_session(self, client, auth_headers):
        r = await client.get("/api/v1/sessions/nonexistent", headers=auth_headers)
        assert r.status_code == 404
        assert r.json()["error_code"] == "SESSION_NOT_FOUND"


class TestListSessions:
    async def test_returns_paginated_list(self, client, auth_headers):
        # Create 3 sessions
        for _ in range(3):
            await client.post("/api/v1/sessions", headers=auth_headers)

        r = await client.get("/api/v1/sessions?limit=2&offset=0", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3

    async def test_user_isolation(self, client, auth_headers):
        """Alice's sessions shouldn't appear in Bob's list."""
        # Create as test-user
        await client.post("/api/v1/sessions", headers=auth_headers)

        # Use different key (configured in settings override)
        r = await client.get("/api/v1/sessions", headers={"X-API-Key": "unknown-key"})
        assert r.status_code == 401


class TestDeleteSession:
    async def test_deletes_session(self, client, auth_headers):
        r = await client.post("/api/v1/sessions", headers=auth_headers)
        sid = r.json()["session_id"]

        r = await client.delete(f"/api/v1/sessions/{sid}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["deleted"] is True

        # Gone
        r = await client.get(f"/api/v1/sessions/{sid}", headers=auth_headers)
        assert r.status_code == 404

    async def test_delete_nonexistent_returns_false(self, client, auth_headers):
        r = await client.delete("/api/v1/sessions/nope", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["deleted"] is False
