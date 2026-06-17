import type { ApiClient } from "./client";
import type { JobRequirements, TaskResponse } from "./types";

export function queueJob(
  api: ApiClient,
  sessionId: string,
  source: { url?: string; text?: string }
): Promise<TaskResponse> {
  return api.post(`/sessions/${sessionId}/jobs`, {
    url: source.url ?? null,
    text: source.text ?? null,
  });
}

export function listJobs(
  api: ApiClient,
  sessionId: string
): Promise<{ jobs: JobRequirements[] }> {
  return api.get(`/sessions/${sessionId}/jobs`);
}

export function removeJob(
  api: ApiClient,
  sessionId: string,
  index: number
): Promise<void> {
  return api.delete(`/sessions/${sessionId}/jobs/${index}`);
}
