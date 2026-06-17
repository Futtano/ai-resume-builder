<script lang="ts">
  import { sessionStore } from "$lib/stores/session.svelte";
  import { ApiClient } from "$lib/api/client";

  let { onSessionSelect }: { onSessionSelect: (id: string) => void } = $props();

  let api = $derived(new ApiClient());

  function handleCreate() {
    sessionStore.createSession(api).then((id) => {
      if (id) onSessionSelect(id);
    });
  }

  function handleDelete(id: string, e: Event) {
    e.stopPropagation();
    sessionStore.deleteSession(api, id);
  }

  // Fetch sessions on mount
  $effect(() => {
    sessionStore.fetchSessions(api);
  });
</script>

<aside class="sidebar">
  <div class="sidebar-header">
    <span class="brand">📄 Resume Builder</span>
    <button class="new-btn" onclick={handleCreate} title="New session">+</button>
  </div>

  <div class="session-list">
    {#if sessionStore.isLoading}
      <p class="empty">Loading...</p>
    {:else if sessionStore.list.length === 0}
      <p class="empty">No sessions yet.<br />Click + to create one.</p>
    {:else}
      {#each sessionStore.list as s}
        <div
          class="session-item"
          class:active={s.session_id === sessionStore.currentId}
          onclick={() => onSessionSelect(s.session_id)}
          role="button"
          tabindex="0"
          onkeydown={(e: KeyboardEvent) => {
            if (e.key === "Enter") onSessionSelect(s.session_id);
          }}
        >
          <div class="session-info">
            <span class="session-name">{s.candidate_name || "Unnamed"}</span>
            <span class="session-meta">
              {s.experience_count} exp · {s.skills_count} skills
              {#if s.job_count > 0} · {s.job_count} jobs{/if}
            </span>
          </div>
          <button
            class="delete-btn"
            onclick={(e: Event) => handleDelete(s.session_id, e)}
            title="Delete session"
          >
            ×
          </button>
        </div>
      {/each}
    {/if}
  </div>

</aside>

<style>
  .sidebar {
    width: var(--sidebar-width);
    height: 100vh;
    display: flex;
    flex-direction: column;
    background: var(--bg-raised);
    border-right: 1px solid var(--border-light);
    flex-shrink: 0;
  }

  .sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px;
    border-bottom: 1px solid var(--border-light);
    box-shadow: var(--elevation-low);
    position: relative;
    z-index: 10;
  }

  .brand {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .new-btn {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--accent);
    color: white;
    border-radius: var(--radius-sm);
    font-size: 18px;
    font-weight: 500;
    transition: background var(--transition-fast);
  }

  .new-btn:hover {
    background: var(--accent-hover);
  }

  .session-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }

  .empty {
    padding: 24px 16px;
    text-align: center;
    font-size: 13px;
    color: var(--text-tertiary);
    line-height: 1.6;
  }

  .session-item {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    border-radius: var(--radius-md);
    text-align: left;
    color: var(--text-primary);
    transition: background var(--transition-fast);
    margin-bottom: 2px;
  }

  .session-item:hover {
    background: var(--bg-inset);
  }

  .session-item.active {
    background: var(--accent-subtle);
  }

  .session-item.active .session-name {
    color: var(--accent);
  }

  .session-info {
    flex: 1;
    min-width: 0;
  }

  .session-name {
    display: block;
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .session-meta {
    display: block;
    font-size: 11px;
    color: var(--text-tertiary);
    margin-top: 2px;
  }

  .delete-btn {
    flex-shrink: 0;
    width: 22px;
    height: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-sm);
    color: var(--text-tertiary);
    font-size: 16px;
    opacity: 0;
    transition: opacity var(--transition-fast), color var(--transition-fast);
  }

  .session-item:hover .delete-btn {
    opacity: 1;
  }

  .delete-btn:hover {
    color: var(--danger);
    background: var(--danger-subtle);
  }
</style>
