<script lang="ts">
  import { theme } from "$lib/stores/theme.svelte";
  import "../app.css";

  theme.syncDOM();

  let { children } = $props();
</script>

{@render children()}
