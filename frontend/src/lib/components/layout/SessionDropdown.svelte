<script lang="ts">
  import { sessionStore } from "$lib/stores/session.svelte";
  import { ApiClient } from "$lib/api/client";

  let { onSessionSelect }: { onSessionSelect: (id: string) => void } = $props();

  let api = $derived(new ApiClient());
  let open = $state(false);
  let triggerRef: HTMLButtonElement | undefined = $state();
  let dropdownRef: HTMLDivElement | undefined = $state();

  function toggle() {
    open = !open;
  }

  function close() {
    open = false;
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      close();
      triggerRef?.focus();
    }
  }

  function handleTriggerKeydown(e: KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      open = true;
    }
    if (e.key === "Escape") {
      close();
    }
  }

  async function handleCreate() {
    const id = await sessionStore.createSession(api);
    if (id) {
      onSessionSelect(id);
      close();
    }
  }

  function handleSelect(id: string) {
    onSessionSelect(id);
    close();
  }

  function handleDelete(id: string, e: Event) {
    e.stopPropagation();
    sessionStore.deleteSession(api, id);
  }

  // Fetch sessions on mount
  $effect(() => {
    sessionStore.fetchSessions(api);
  });

  // Click outside: use a window capture listener so we catch the click
  // before any other handler can stop propagation
  $effect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      const target = e.target as Node;
      if (dropdownRef && !dropdownRef.contains(target) && triggerRef && !triggerRef.contains(target)) {
        close();
      }
    }
    // Use capture phase to catch clicks before they might be stopped
    window.addEventListener("click", onClick, true);
    return () => window.removeEventListener("click", onClick, true);
  });
</script>

<button
  class="trigger"
  class:open
  bind:this={triggerRef}
  onclick={toggle}
  onkeydown={handleTriggerKeydown}
  aria-haspopup="listbox"
  aria-expanded={open}
>
  <span class="trigger-label">
    {sessionStore.current?.candidate_name || "Select Session"}
  </span>
  <svg
    class="chevron"
    class:rotated={open}
    width="12"
    height="12"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2.5"
    stroke-linecap="round"
    stroke-linejoin="round"
  >
    <polyline points="6 9 12 15 18 9" />
  </svg>
</button>

{#if open}
  <div class="backdrop"></div>
  <div
    class="dropdown"
    bind:this={dropdownRef}
    onkeydown={handleKeydown}
    role="listbox"
    tabindex="0"
  >
    <div class="dropdown-header">
      <span class="dropdown-title">Resumes</span>
      <button class="new-btn" onclick={handleCreate} title="New session">+</button>
    </div>

    <div class="dropdown-list">
      {#if sessionStore.isLoading}
        <p class="empty">Loading...</p>
      {:else if sessionStore.list.length === 0}
        <p class="empty">No sessions yet.<br />Click + to create one.</p>
      {:else}
        {#each sessionStore.list as s}
          <button
            class="session-item"
            class:active={s.session_id === sessionStore.currentId}
            onclick={() => handleSelect(s.session_id)}
            role="option"
            aria-selected={s.session_id === sessionStore.currentId}
          >
            <div class="session-info">
              <span class="session-name">{s.candidate_name || "Unnamed"}</span>
              <span class="session-meta">
                {s.experience_count} exp · {s.skills_count} skills
                {#if s.job_count > 0} · {s.job_count} jobs{/if}
              </span>
            </div>
            <span
              class="delete-btn"
              onclick={(e: Event) => handleDelete(s.session_id, e)}
              title="Delete session"
              role="button"
              tabindex="0"
              onkeydown={(e: KeyboardEvent) => { if (e.key === 'Enter') handleDelete(s.session_id, e); }}
            >
              ×
            </span>
          </button>
        {/each}
      {/if}
    </div>

  </div>
{/if}

<style>
  .trigger {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 28px;
    padding: 0 8px;
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-size: 13px;
    font-weight: 500;
    transition: background var(--transition-fast);
    white-space: nowrap;
  }

  .trigger:hover,
  .trigger.open {
    background: var(--bg-inset);
  }

  .trigger-label {
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chevron {
    color: var(--text-tertiary);
    transition: transform 0.15s ease;
    flex-shrink: 0;
  }

  .chevron.rotated {
    transform: rotate(180deg);
  }

  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 99;
  }

  .dropdown {
    position: absolute;
    top: calc(var(--topbar-height) - 4px);
    left: 8px;
    width: 280px;
    background: var(--bg-raised);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    z-index: 100;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .dropdown-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px 8px;
  }

  .dropdown-title {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-tertiary);
  }

  .new-btn {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--accent);
    color: white;
    border-radius: var(--radius-sm);
    font-size: 16px;
    font-weight: 500;
    transition: background var(--transition-fast);
  }

  .new-btn:hover {
    background: var(--accent-hover);
  }

  .dropdown-list {
    max-height: 60vh;
    overflow-y: auto;
    padding: 4px 8px;
  }

  .empty {
    padding: 20px 16px;
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
    padding: 8px 10px;
    border-radius: var(--radius-sm);
    text-align: left;
    color: var(--text-primary);
    transition: background var(--transition-fast);
    margin-bottom: 1px;
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
