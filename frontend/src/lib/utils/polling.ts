/** Task polling utility for async backend operations. */

import type { ApiClient } from "$lib/api/client";
import { getTaskStatus } from "$lib/api/tasks";
import type { TaskStatusResponse } from "$lib/api/types";

export interface PollOptions {
  intervalMs?: number;
  maxAttempts?: number;
  onProgress?: (status: TaskStatusResponse) => void;
}

const DEFAULT_INTERVAL = 1500;
const DEFAULT_MAX_ATTEMPTS = 120; // 3 minutes at 1.5s intervals

export function pollTask(
  api: ApiClient,
  taskId: string,
  options: PollOptions = {}
): Promise<TaskStatusResponse> {
  const { intervalMs = DEFAULT_INTERVAL, maxAttempts = DEFAULT_MAX_ATTEMPTS, onProgress } = options;

  return new Promise((resolve, reject) => {
    let attempts = 0;
    let timer: ReturnType<typeof setTimeout>;

    const tick = async () => {
      attempts++;
      try {
        const status = await getTaskStatus(api, taskId);
        onProgress?.(status);

        if (status.status === "completed") {
          clearTimeout(timer);
          resolve(status);
        } else if (status.status === "failed") {
          clearTimeout(timer);
          reject(
            new Error(
              status.error?.detail ?? "Task failed"
            )
          );
        } else if (status.status === "not_found") {
          clearTimeout(timer);
          reject(new Error("Task not found — server may have restarted"));
        } else if (attempts >= maxAttempts) {
          clearTimeout(timer);
          reject(new Error("Task timed out"));
        } else {
          timer = setTimeout(tick, intervalMs);
        }
      } catch (err) {
        if (attempts >= maxAttempts) {
          clearTimeout(timer);
          reject(err);
        } else {
          timer = setTimeout(tick, intervalMs);
        }
      }
    };

    tick();
  });
}
