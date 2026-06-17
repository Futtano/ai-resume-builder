import type { ApiClient } from "./client";
import type { ExportItem, TaskResponse } from "./types";

export interface TailorStatusResponse {
  status: string;
  total_jobs: number;
  completed_jobs: number;
  errors: string[];
}

export function runTailoring(
  api: ApiClient,
  sessionId: string
): Promise<TaskResponse> {
  return api.post(`/sessions/${sessionId}/tailor`);
}

export function getTailorStatus(
  api: ApiClient,
  sessionId: string
): Promise<TailorStatusResponse> {
  return api.get(`/sessions/${sessionId}/tailor/status`);
}

export function generateExports(
  api: ApiClient,
  sessionId: string
): Promise<ExportItem[]> {
  return api.post(`/sessions/${sessionId}/exports`);
}

export function listExports(
  api: ApiClient,
  sessionId: string
): Promise<{ exports: ExportItem[] }> {
  return api.get(`/sessions/${sessionId}/exports`);
}

export function getExportDownloadUrl(
  sessionId: string,
  filename: string
): string {
  return `/api/v1/sessions/${sessionId}/exports/${filename}`;
}
