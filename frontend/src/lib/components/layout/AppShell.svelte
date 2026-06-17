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

  // Panel ratio: fraction for left panel, persisted to localStorage
  let leftRatio = $state(loadRatio());

  function loadRatio(): number {
    try {
      const stored = globalThis.localStorage?.getItem("panel_ratio");
      if (stored) {
        const n = parseFloat(stored);
        if (n >= 0.3 && n <= 0.7) return n;
      }
    } catch {
      // localStorage unavailable (SSR, private browsing, etc.)
    }
    return 0.45;
  }

  $effect(() => {
    try {
      globalThis.localStorage?.setItem("panel_ratio", String(leftRatio));
    } catch {
      // ignore
    }
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

<div class="app-shell">
  <TopBar {onSessionSelect} />

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
</style>
