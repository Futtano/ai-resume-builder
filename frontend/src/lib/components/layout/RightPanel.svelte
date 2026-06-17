<script lang="ts">
  import ResumeToolbar from "../resume/ResumeToolbar.svelte";
  import PreviewPane from "../resume/PreviewPane.svelte";
  import type { ApiClient } from "$lib/api/client";

  let {
    api,
    style = "",
  }: {
    api: ApiClient;
    style?: string;
  } = $props();
</script>

<div class="right-panel" {style}>
  <div class="right-panel-header">
    <ResumeToolbar {api} />
  </div>
  <div class="preview-content-area">
    <PreviewPane {api} />
  </div>
</div>

<style>
  .right-panel {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-width: var(--panel-min-width);
    background: var(--bg-inset);
    overflow: hidden;
  }

  .right-panel-header {
    height: 32px;
    display: flex;
    align-items: center;
    padding: 0 16px;
    background: var(--bg-raised);
    border-bottom: 1px solid var(--border-light);
    box-shadow: var(--elevation-low);
    position: relative;
    z-index: 10;
    flex-shrink: 0;
  }
</style>
