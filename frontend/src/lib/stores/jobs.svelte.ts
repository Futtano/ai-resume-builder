/** Jobs store — queued job postings. */

import type { ApiClient } from "$lib/api/client";
import * as jobsApi from "$lib/api/jobs";
import type { JobRequirements } from "$lib/api/types";

class JobsStore {
  jobs = $state<JobRequirements[]>([]);
  isLoading = $state(false);
  error = $state<string | null>(null);

  async fetchJobs(api: ApiClient, sessionId: string) {
    this.isLoading = true;
    this.error = null;
    try {
      const res = await jobsApi.listJobs(api, sessionId);
      this.jobs = res.jobs ?? [];
    } catch (err) {
      this.error = err instanceof Error ? err.message : "Failed to load jobs";
    } finally {
      this.isLoading = false;
    }
  }

  async queueJob(
    api: ApiClient,
    sessionId: string,
    source: { url?: string; text?: string },
    pollTask: (taskId: string) => Promise<unknown>
  ) {
    this.error = null;
    try {
      const { task_id } = await jobsApi.queueJob(api, sessionId, source);
      await pollTask(task_id);
      await this.fetchJobs(api, sessionId);
    } catch (err) {
      this.error = err instanceof Error ? err.message : "Failed to queue job";
    }
  }

  async removeJob(api: ApiClient, sessionId: string, index: number) {
    this.error = null;
    try {
      await jobsApi.removeJob(api, sessionId, index);
      this.jobs = this.jobs.filter((_, i) => i !== index);
    } catch (err) {
      this.error = err instanceof Error ? err.message : "Failed to remove job";
    }
  }
}

export const jobsStore = new JobsStore();
