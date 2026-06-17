import type { ApiClient } from "./client";
import type { SessionListResponse, SessionSummary, TaskResponse } from "./types";

export function createSession(api: ApiClient): Promise<SessionSummary & { session_id: string }> {
  return api.post("/sessions");
}

export function listSessions(
  api: ApiClient,
  limit = 20,
  offset = 0
): Promise<SessionListResponse> {
  return api.get("/sessions", { limit: String(limit), offset: String(offset) });
}

export function getSession(api: ApiClient, sessionId: string): Promise<unknown> {
  return api.get(`/sessions/${sessionId}`);
}

export function deleteSession(api: ApiClient, sessionId: string): Promise<unknown> {
  return api.delete(`/sessions/${sessionId}`);
}
