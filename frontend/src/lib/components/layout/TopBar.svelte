<script lang="ts">
  import { goto } from "$app/navigation";
  import { auth } from "$lib/stores/auth.svelte";
  import SessionDropdown from "./SessionDropdown.svelte";
  import ThemeToggle from "./ThemeToggle.svelte";

  let { onSessionSelect }: { onSessionSelect: (id: string) => void } = $props();

  function handleLogout() {
    auth.logout();
    goto("/", { replaceState: true });
  }
</script>

<div class="topbar">
  <div class="topbar-left">
    <SessionDropdown {onSessionSelect} />
  </div>
  <div class="topbar-right">
    <button
      class="logout-btn"
      onclick={handleLogout}
      type="button"
      aria-label="Sign out"
      title="Sign out"
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
        <polyline points="16 17 21 12 16 7" />
        <line x1="21" y1="12" x2="9" y2="12" />
      </svg>
    </button>
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
    gap: 8px;
    margin-right: 12px;
  }

  .logout-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 28px;
    border-radius: 6px;
    color: var(--text-tertiary);
    background: transparent;
    transition: color 0.2s ease, background 0.2s ease;
  }

  .logout-btn:hover {
    color: var(--text-primary);
    background: var(--bg-inset);
  }

  .logout-btn:active {
    color: var(--accent);
  }
</style>
