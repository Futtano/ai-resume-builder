<script lang="ts">
  import ChatPanel from "../chat/ChatPanel.svelte";
  import type { ApiClient } from "$lib/api/client";

  let {
    api,
    pollFn,
    style = "",
  }: {
    api: ApiClient;
    pollFn: (taskId: string) => Promise<unknown>;
    style?: string;
  } = $props();
</script>

<div class="left-panel" {style}>
  <div class="left-panel-content">
    <ChatPanel {api} {pollFn} />
  </div>
</div>

<style>
  .left-panel {
    position: relative;
    display: flex;
    flex-direction: column;
    min-width: var(--panel-min-width);
    overflow: hidden;
    background: var(--bg-raised);
  }

  .left-panel-content {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }
</style>
