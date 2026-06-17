<script lang="ts">
  import { renderAsync } from "docx-preview";
  import LoadingSpinner from "../common/LoadingSpinner.svelte";

  let { docxBlob }: { docxBlob: Blob | null } = $props();

  let containerEl = $state<HTMLDivElement>();
  let isLoading = $state(false);
  let error = $state<string | null>(null);

  $effect(() => {
    const blob = docxBlob;
    const container = containerEl;
    if (!blob || !container) return;

    let cancelled = false;
    isLoading = true;
    error = null;
    container.innerHTML = "";

    renderAsync(blob, container, undefined, {
      className: "docx",
      inWrapper: true,
      ignoreWidth: true,
      ignoreHeight: true,
      breakPages: true,
      ignoreLastRenderedPageBreak: true,
    })
      .then(() => {
        if (!cancelled) isLoading = false;
      })
      .catch((err: Error) => {
        if (!cancelled) {
          error = err.message;
          isLoading = false;
        }
      });

    return () => {
      cancelled = true;
    };
  });
</script>

<div class="docx-preview-container">
  {#if isLoading}
    <div class="loading-overlay">
      <LoadingSpinner size={24} />
      <span>Rendering preview...</span>
    </div>
  {:else if error}
    <div class="error-state">
      <span class="error-icon">⚠️</span>
      <p>Preview failed: {error}</p>
    </div>
  {:else if !docxBlob}
    <div class="empty-state">
      <div class="empty-icon">📄</div>
      <p class="empty-title">No resume to preview</p>
      <p class="empty-hint">
        Upload a PDF resume or start chatting to build one from scratch.
      </p>
    </div>
  {/if}
  <div bind:this={containerEl} class="docx-paper"></div>
</div>

<style>
  .docx-preview-container {
    height: 100%;
    width: 100%;
    overflow-y: auto;
    position: relative;
  }

  .loading-overlay {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    margin-top: 60px;
    color: var(--text-secondary);
    font-size: 14px;
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    z-index: 2;
  }

  .error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    margin-top: 60px;
    color: var(--text-error, #dc2626);
    font-size: 14px;
    text-align: center;
  }

  .error-icon {
    font-size: 32px;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    height: 100%;
    color: var(--text-secondary);
  }

  .empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
    opacity: 0.5;
  }

  .empty-title {
    font-size: 16px;
    font-weight: 500;
    color: var(--text-primary);
    margin-bottom: 8px;
  }

  .empty-hint {
    font-size: 13px;
    color: var(--text-tertiary);
    max-width: 280px;
    line-height: 1.5;
  }
</style>
