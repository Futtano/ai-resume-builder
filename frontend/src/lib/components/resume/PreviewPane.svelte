<script lang="ts">
  import { resumeStore } from "$lib/stores/resume.svelte";
  import { sessionStore } from "$lib/stores/session.svelte";
  import DocxPreview from "./DocxPreview.svelte";
  import type { ApiClient } from "$lib/api/client";

  let { api }: { api: ApiClient } = $props();

  $effect(() => {
    // Refresh preview when session changes
    const sid = sessionStore.currentId;
    if (sid) {
      resumeStore.fetchPreview(api, sid);
    }
  });
</script>

<div class="preview-pane">
  <DocxPreview docxBlob={resumeStore.previewDocx} />
</div>

<style>
  .preview-pane {
    height: 100%;
    width: 100%;
  }
</style>
