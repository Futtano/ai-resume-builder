<script lang="ts">
  import { jobsStore } from "$lib/stores/jobs.svelte";
  import type { ApiClient } from "$lib/api/client";
  import type { JobRequirements } from "$lib/api/types";

  let { api, sessionId }: { api: ApiClient; sessionId: string | null } = $props();

  function handleRemove(index: number) {
    if (!sessionId) return;
    jobsStore.removeJob(api, sessionId, index);
  }
</script>

{#if jobsStore.jobs.length > 0}
  <div class="job-list">
    <h3 class="section-title">Jobs for Tailoring ({jobsStore.jobs.length})</h3>
    {#each jobsStore.jobs as job, i}
      <div class="job-item">
        <div class="job-info">
          <span class="job-title">{job.job_title}</span>
          <span class="job-company">{job.company}</span>
        </div>
        <button
          class="remove-btn"
          onclick={() => handleRemove(i)}
          title="Remove job"
        >×</button>
      </div>
    {/each}
  </div>
{/if}

<style>
  .job-list {
    padding: 12px 16px;
    border-top: 1px solid var(--border-light);
  }

  .section-title {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
  }

  .job-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    border-radius: var(--radius-sm);
    background: var(--bg-raised);
    border: 1px solid var(--border-light);
    margin-bottom: 4px;
  }

  .job-info {
    flex: 1;
    min-width: 0;
  }

  .job-title {
    display: block;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .job-company {
    display: block;
    font-size: 11px;
    color: var(--text-tertiary);
    margin-top: 1px;
  }

  .remove-btn {
    flex-shrink: 0;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-sm);
    color: var(--text-tertiary);
    font-size: 14px;
    transition: color var(--transition-fast);
  }

  .remove-btn:hover {
    color: var(--danger);
  }
</style>
