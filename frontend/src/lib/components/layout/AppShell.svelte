<script lang="ts">
  import TopBar from "./TopBar.svelte";
  import LeftPanel from "./LeftPanel.svelte";
  import PanelResizer from "./PanelResizer.svelte";
  import RightPanel from "./RightPanel.svelte";
  import { sessionStore } from "$lib/stores/session.svelte";
  import { resumeStore } from "$lib/stores/resume.svelte";
  import { chatStore } from "$lib/stores/chat.svelte";
  import { jobsStore } from "$lib/stores/jobs.svelte";
  import { ApiClient } from "$lib/api/client";
  import { pollTask } from "$lib/utils/polling";

  let api = $derived(new ApiClient());
  let containerRef: HTMLDivElement | undefined = $state();

  let leftRatio = $state(loadRatio());
  let mobileView = $state<"chat" | "preview">("chat");

  function loadRatio(): number {
    try {
      const stored = globalThis.localStorage?.getItem("panel_ratio");
      if (stored) {
        const n = parseFloat(stored);
        if (n >= 0.3 && n <= 0.7) return n;
      }
    } catch { /* ignore */ }
    return 0.45;
  }

  $effect(() => {
    try { globalThis.localStorage?.setItem("panel_ratio", String(leftRatio)); } catch { /* ignore */ }
  });

  function handleResize(clientX: number) {
    if (!containerRef) return;
    const rect = containerRef.getBoundingClientRect();
    const ratio = (clientX - rect.left) / rect.width;
    leftRatio = Math.max(0.3, Math.min(0.7, ratio));
  }

  async function onSessionSelect(id: string) {
    sessionStore.selectSession(id);
    await Promise.all([
      resumeStore.fetchResume(api, id),
      resumeStore.fetchPreview(api, id),
      chatStore.fetchConversation(api, id),
      jobsStore.fetchJobs(api, id),
    ]);
  }

  function createPollFn(apiClient: ApiClient) {
    return (taskId: string) => pollTask(apiClient, taskId);
  }

  let leftStyle = $derived(`flex: 0 0 ${leftRatio * 100}%`);
  let rightStyle = $derived(`flex: 1`);
</script>

<div class="app-shell" data-mobile-view={mobileView}>
  <TopBar {onSessionSelect} />

  <div class="mobile-tabs">
    <div class="mobile-tabs-inner">
      <button class="mobile-tab" class:active={mobileView === "chat"} onclick={() => (mobileView = "chat")}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
        Chat
      </button>
      <span class="mobile-tabs-sep"></span>
      <button class="mobile-tab" class:active={mobileView === "preview"} onclick={() => (mobileView = "preview")}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
        Preview
      </button>
    </div>
  </div>

  <div class="panels-container" id="panels-container" bind:this={containerRef}>
    <LeftPanel {api} pollFn={createPollFn(api)} style={leftStyle} />
    <PanelResizer onResize={handleResize} />
    <RightPanel {api} style={rightStyle} />
  </div>
</div>

<style>
  .app-shell {
    display: flex;
    flex-direction: column;
    height: 100vh;
    width: 100vw;
    overflow: hidden;
  }

  .panels-container {
    display: flex;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  /* ── Mobile tabs ── */
  .mobile-tabs {
    display: none;
  }

  .mobile-tabs-inner {
    display: flex;
    flex-direction: row;
    flex-wrap: nowrap;
    align-items: center;
    justify-content: center;
    width: 100%;
  }

  .mobile-tab {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-tertiary);
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    transition: color 0.2s ease, border-color 0.2s ease;
    flex-shrink: 0;
  }

  .mobile-tab:hover { color: var(--text-secondary); }
  .mobile-tab.active { color: var(--accent); border-bottom-color: var(--accent); }

  .mobile-tabs-sep {
    width: 1px;
    height: 20px;
    background: var(--border-light);
    flex-shrink: 0;
    margin: 0 4px;
  }

  /* ── Mobile layout (≤768px) ── */
  @media (max-width: 768px) {
    .mobile-tabs {
      display: flex;
      align-items: center;
      padding: 0 12px;
      background: var(--bg-raised);
      border-bottom: 1px solid var(--border-light);
      flex-shrink: 0;
    }

    /* Hide resizer */
    .panels-container :global(.panel-resizer) {
      display: none;
    }

    /* Both panels: fill container, only one visible */
    .panels-container :global(.left-panel),
    .panels-container :global(.right-panel) {
      flex: 1 !important;
      min-width: 0 !important;
      align-self: stretch !important;
    }

    /* Hide based on data-mobile-view */
    .app-shell[data-mobile-view="chat"] :global(.right-panel) {
      display: none;
    }
    .app-shell[data-mobile-view="preview"] :global(.left-panel) {
      display: none;
    }
  }
</style>
