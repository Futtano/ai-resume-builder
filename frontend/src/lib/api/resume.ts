import type { ApiClient } from "./client";
import type { EditResumeResponse, ParsedResume, TaskResponse } from "./types";

export interface ResumeUploadResponse {
  filename: string;
  size: number;
}

export function uploadResume(
  api: ApiClient,
  sessionId: string,
  file: File
): Promise<ResumeUploadResponse> {
  const fd = new FormData();
  fd.append("file", file);
  return api.upload(`/sessions/${sessionId}/resume`, fd);
}

export function triggerParse(
  api: ApiClient,
  sessionId: string
): Promise<TaskResponse> {
  return api.post(`/sessions/${sessionId}/resume/parse`);
}

export function getResume(
  api: ApiClient,
  sessionId: string
): Promise<{ working_resume: ParsedResume | null }> {
  return api.get(`/sessions/${sessionId}/resume`);
}

export function editResume(
  api: ApiClient,
  sessionId: string,
  instruction: string
): Promise<EditResumeResponse> {
  return api.patch(`/sessions/${sessionId}/resume`, { instruction });
}

export function getResumePreview(
  api: ApiClient,
  sessionId: string
): Promise<Blob> {
  return api.get(`/sessions/${sessionId}/resume/preview.docx`);
}
