import type { ApiClient } from "./client";
import type { TaskStatusResponse } from "./types";

export function getTaskStatus(
  api: ApiClient,
  taskId: string
): Promise<TaskStatusResponse> {
  return api.get(`/tasks/${taskId}`);
}
