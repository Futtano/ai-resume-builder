<script lang="ts">
  import SessionDropdown from "./SessionDropdown.svelte";
  import ThemeToggle from "./ThemeToggle.svelte";

  let { onSessionSelect }: { onSessionSelect: (id: string) => void } = $props();
</script>

<div class="topbar">
  <div class="topbar-left">
    <SessionDropdown {onSessionSelect} />
  </div>
  <div class="topbar-right">
    <ThemeToggle />
  </div>
</div>

<style>
  .topbar-left {
    display: flex;
    align-items: center;
  }

  .topbar-right {
    display: flex;
    align-items: center;
    margin-right: 12px;
  }
</style>
