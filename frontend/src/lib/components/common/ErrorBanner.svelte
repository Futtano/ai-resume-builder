<script lang="ts">
  let { message, onDismiss }: { message: string; onDismiss?: () => void } = $props();
</script>

{#if message}
  <div class="error-banner">
    <span class="error-text">{message}</span>
    {#if onDismiss}
      <button class="dismiss" onclick={onDismiss} aria-label="Dismiss">×</button>
    {/if}
  </div>
{/if}

<style>
  .error-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 10px 14px;
    background: var(--danger-subtle);
    border: 1px solid var(--danger);
    border-radius: var(--radius-md);
    color: var(--danger);
    font-size: 13px;
    animation: slideIn 0.2s ease;
  }
  .dismiss {
    flex-shrink: 0;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-sm);
    color: var(--danger);
    font-size: 16px;
    line-height: 1;
  }
  .dismiss:hover {
    background: var(--danger);
    color: white;
  }
  @keyframes slideIn {
    from { opacity: 0; transform: translateY(-4px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
