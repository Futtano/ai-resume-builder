<script lang="ts">
  import { sessionStore } from "$lib/stores/session.svelte";
  import { jobsStore } from "$lib/stores/jobs.svelte";
  import { resumeStore } from "$lib/stores/resume.svelte";
  import type { ApiClient } from "$lib/api/client";
  import * as tailoringApi from "$lib/api/tailoring";
  import { pollTask } from "$lib/utils/polling";

  let {
    api,
  }: {
    api: ApiClient;
  } = $props();

  let isTailoring = $state(false);
  let isExporting = $state(false);
  let exports = $state<Awaited<ReturnType<typeof tailoringApi.listExports>>["exports"]>([]);

  function triggerDownload(filename: string) {
    const sid = sessionStore.currentId;
    if (!sid) return;
    const url = tailoringApi.getExportDownloadUrl(sid, filename);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    a.remove();
  }

  async function handleTailor() {
    const sid = sessionStore.currentId;
    if (!sid) return;

    isTailoring = true;
    try {
      const { task_id } = await tailoringApi.runTailoring(api, sid);
      await pollTask(api, task_id, {
        onProgress: (s) => {
          if (s.status === "running") {
            // Could update a progress bar here
          }
        },
      });
      await resumeStore.fetchPreview(api, sid);

      // Auto-generate exports after tailoring so the download button appears ready
      await tailoringApi.generateExports(api, sid);
      await loadExports();
    } catch (err) {
      resumeStore.editError = err instanceof Error ? err.message : "Tailoring failed";
    } finally {
      isTailoring = false;
    }
  }

  async function handleExport() {
    const sid = sessionStore.currentId;
    if (!sid || exports.length === 0) return;

    // If exports are already loaded, download the first one directly
    triggerDownload(exports[0].filename);
  }

  async function loadExports() {
    const sid = sessionStore.currentId;
    if (!sid) return;
    try {
      const res = await tailoringApi.listExports(api, sid);
      exports = res.exports ?? [];
    } catch {
      // exports may not be available
    }
  }

  // Load exports when session changes
  $effect(() => {
    if (sessionStore.currentId) {
      loadExports();
    } else {
      exports = [];
    }
  });

  let canTailor = $derived(
    jobsStore.jobs.length > 0 && resumeStore.workingResume !== null
  );
</script>

<div class="toolbar">
  <div class="toolbar-actions">
    <button
      class="action-btn tailor-btn"
      onclick={handleTailor}
      disabled={!canTailor || isTailoring}
    >
      {isTailoring ? "Tailoring..." : "Tailor Resume"}
    </button>

    {#if exports.length > 0}
      <button
        class="action-btn export-btn"
        onclick={handleExport}
        disabled={isExporting}
      >
        Download
      </button>
    {/if}
  </div>
</div>

<style>
  .toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .toolbar-actions {
    display: flex;
    gap: 6px;
  }

  .action-btn {
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 500;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--text-secondary);
    border: none;
    line-height: 1.6;
    transition: background var(--transition-fast), color var(--transition-fast), opacity var(--transition-fast);
  }

  .action-btn:hover:not(:disabled) {
    background: var(--accent-subtle);
    color: var(--accent);
  }

  .action-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }
</style>
