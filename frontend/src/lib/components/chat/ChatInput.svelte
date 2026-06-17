<script lang="ts">
  let {
    onSubmit,
    onUpload,
    disabled = false,
  }: {
    onSubmit: (text: string) => void;
    onUpload: (file: File) => void;
    disabled?: boolean;
  } = $props();

  let text = $state("");
  let textareaRef: HTMLTextAreaElement | undefined = $state();
  let fileInput: HTMLInputElement | undefined = $state();

  function handleInput() {
    if (!textareaRef) return;
    textareaRef.style.height = "auto";
    textareaRef.style.height = Math.min(textareaRef.scrollHeight, 150) + "px";
    textareaRef.style.overflowY = textareaRef.scrollHeight > 150 ? "auto" : "hidden";
  }

  function handleSubmit(e: Event) {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    text = "";
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  function handleFileChange(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      onUpload(file);
      input.value = "";
    }
  }

  const hasContent = $derived(text.trim().length > 0);
</script>

<form class="chat-input" class:disabled onsubmit={handleSubmit}>
  <div class="input-area">
    <textarea
      class="text-input"
      bind:value={text}
      bind:this={textareaRef}
      onkeydown={handleKeydown}
      oninput={handleInput}
      placeholder="Describe changes to your resume..."
      rows={1}
      disabled={disabled}
    ></textarea>
  </div>

  <div class="action-bar">
    <div class="action-start">
      <button
        type="button"
        class="action-btn upload-btn"
        onclick={() => fileInput?.click()}
        disabled={disabled}
        title="Upload resume PDF"
        aria-label="Upload resume PDF"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
      </button>

      <input
        type="file"
        class="file-input"
        accept=".pdf"
        bind:this={fileInput}
        onchange={handleFileChange}
        aria-label="Choose PDF file"
      />
    </div>

    <button
      type="submit"
      class="send-btn"
      class:active={hasContent}
      disabled={disabled || !hasContent}
      aria-label="Send message"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 19V5" />
        <polyline points="5 12 12 5 19 12" />
      </svg>
    </button>
  </div>
</form>

<style>
  .chat-input {
    padding: 8px;
    border-radius: 24px;
    border: 1px solid var(--border-default);
    background: var(--bg-raised);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    transition: opacity var(--transition-fast), border-color var(--transition-fast), box-shadow var(--transition-fast);
  }

  .chat-input.disabled {
    opacity: 0.5;
  }

  .chat-input:focus-within {
    border-color: var(--accent);
    box-shadow: 0 2px 12px var(--accent-subtle);
  }

  .input-area {
    padding: 0;
  }

  .text-input {
    display: block;
    width: 100%;
    resize: none;
    border: none;
    outline: none;
    background: transparent;
    color: var(--text-primary);
    font-size: 14px;
    line-height: 1.5;
    padding: 4px 12px;
    min-height: 28px;
    max-height: 150px;
    overflow: hidden;
    font-family: inherit;
  }

  .text-input::placeholder {
    color: var(--text-tertiary);
  }

  .text-input:disabled {
    cursor: not-allowed;
  }

  /* Custom scrollbar for textarea */
  .text-input::-webkit-scrollbar {
    width: 6px;
  }
  .text-input::-webkit-scrollbar-track {
    background: transparent;
  }
  .text-input::-webkit-scrollbar-thumb {
    background: var(--border-default);
    border-radius: 3px;
  }
  .text-input::-webkit-scrollbar-thumb:hover {
    background: var(--text-tertiary);
  }

  .action-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 8px;
  }

  .action-start {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .action-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: none;
    background: transparent;
    color: var(--text-tertiary);
    cursor: pointer;
    transition: color var(--transition-fast), background var(--transition-fast);
    flex-shrink: 0;
  }

  .action-btn:hover:not(:disabled) {
    background: var(--accent-subtle);
    color: var(--text-secondary);
  }

  .action-btn:disabled {
    cursor: not-allowed;
    opacity: 0.4;
  }

  .send-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: none;
    background: transparent;
    color: var(--text-tertiary);
    cursor: pointer;
    transition: color var(--transition-fast), background var(--transition-fast);
    flex-shrink: 0;
  }

  .send-btn.active {
    background: var(--text-primary);
    color: var(--bg-surface);
  }

  .send-btn.active:hover:not(:disabled) {
    opacity: 0.85;
  }

  .send-btn:not(.active):hover:not(:disabled) {
    background: var(--accent-subtle);
    color: var(--text-secondary);
  }

  .send-btn:disabled {
    cursor: not-allowed;
    opacity: 0.4;
  }

  .file-input {
    display: none;
  }
</style>
