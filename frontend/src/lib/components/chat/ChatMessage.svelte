<script lang="ts">
  import type { ConversationEntry } from "$lib/api/types";
  import { formatTimestamp } from "$lib/utils/format";

  let { entry }: { entry: ConversationEntry } = $props();
</script>

<div class="message" class:system={entry.intent !== "user"}>
  <div class="message-bubble">
    {#if entry.user_input}
      <p class="user-input">{entry.user_input}</p>
    {/if}
    {#if entry.result_summary}
      <p class="result-summary">{entry.result_summary}</p>
    {/if}
  </div>
  <span class="timestamp">{formatTimestamp(entry.timestamp)}</span>
</div>

<style>
  .message {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 12px;
    animation: message-in 0.2s ease;
  }

  .message-bubble {
    padding: 10px 14px;
    border-radius: var(--radius-md);
    font-size: 13px;
    line-height: 1.5;
  }

  .message:not(.system) .message-bubble {
    background: rgb(var(--accent-rgb) / 0.12);
    color: var(--text-primary);
    align-self: flex-end;
    border-bottom-right-radius: var(--radius-sm);
  }

  .message.system .message-bubble {
    background: rgb(var(--accent-rgb) / 0.06);
    color: var(--text-primary);
    border-bottom-left-radius: var(--radius-sm);
  }

  .user-input {
    white-space: pre-wrap;
    word-break: break-word;
  }

  .result-summary {
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px solid var(--border-light);
    font-size: 12px;
    color: var(--text-secondary);
  }

  /* Dark mode: stronger accent tint for better contrast */
  :global([data-theme="dark"]) .message:not(.system) .message-bubble {
    background: rgb(var(--accent-rgb) / 0.22);
    color: var(--text-primary);
  }

  :global([data-theme="dark"]) .message.system .message-bubble {
    background: rgb(var(--accent-rgb) / 0.1);
    color: var(--text-primary);
  }

  :global([data-theme="dark"]) .message:not(.system) .result-summary {
    border-top-color: rgba(255, 255, 255, 0.15);
    color: rgba(255, 255, 255, 0.75);
  }

  .timestamp {
    font-size: 11px;
    color: var(--text-tertiary);
    padding: 0 4px;
  }
</style>
