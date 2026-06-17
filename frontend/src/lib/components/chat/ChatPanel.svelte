<script lang="ts">
  import ChatMessage from "./ChatMessage.svelte";
  import ChatInput from "./ChatInput.svelte";
  import JobList from "./JobList.svelte";
  import ErrorBanner from "../common/ErrorBanner.svelte";
  import LoadingSpinner from "../common/LoadingSpinner.svelte";
  import { chatStore } from "$lib/stores/chat.svelte";
  import { resumeStore } from "$lib/stores/resume.svelte";
  import { jobsStore } from "$lib/stores/jobs.svelte";
  import { sessionStore } from "$lib/stores/session.svelte";
  import type { ApiClient } from "$lib/api/client";

  let {
    api,
    pollFn,
  }: {
    api: ApiClient;
    pollFn: (taskId: string) => Promise<unknown>;
  } = $props();

  let messagesEnd: HTMLDivElement | undefined = $state();

  function scrollToBottom() {
    messagesEnd?.scrollIntoView({ behavior: "smooth" });
  }

  async function handleSubmit(text: string) {
    const sid = sessionStore.currentId;
    if (!sid) return;

    // Detect job URLs in the input
    const urlMatch = text.match(/https?:\/\/\S+/);
    if (urlMatch) {
      await jobsStore.queueJob(api, sid, { url: urlMatch[0] }, pollFn);
    }

    const entry = await resumeStore.applyEdit(api, sid, text);
    if (entry) {
      chatStore.addMessage(entry);
    }
    scrollToBottom();
  }

  async function handleUpload(file: File) {
    const sid = sessionStore.currentId;
    if (!sid) return;
    await resumeStore.uploadAndParse(api, sid, file, pollFn);
    scrollToBottom();
  }

  $effect(() => {
    scrollToBottom();
  });
</script>

<div class="chat-panel">
  <!-- Error display -->
  {#if resumeStore.editError}
    <ErrorBanner message={resumeStore.editError} onDismiss={() => (resumeStore.editError = null)} />
  {/if}

  <!-- Messages -->
  <div class="messages-container">
    {#if sessionStore.currentId === null}
      <div class="empty-state">
        <p>Select or create a session to get started.</p>
      </div>
    {:else if chatStore.messages.length === 0 && resumeStore.workingResume === null}
      <div class="empty-state">
        <p>No resume loaded yet.</p>
        <p class="hint">Upload a PDF resume or start describing your experience.</p>
      </div>
    {:else}
      {#each chatStore.messages as msg}
        <ChatMessage entry={msg} />
      {/each}
      {#if resumeStore.isEditing}
        <div class="editing-indicator">
          <LoadingSpinner size={16} />
          <span>Updating resume...</span>
        </div>
      {/if}
      <div bind:this={messagesEnd}></div>
    {/if}
  </div>

  <!-- Job list (collapsible section at bottom of chat) -->
  <JobList {api} sessionId={sessionStore.currentId} />

  <!-- Input -->
  <ChatInput
    onSubmit={handleSubmit}
    onUpload={handleUpload}
    disabled={resumeStore.isEditing || sessionStore.currentId === null}
  />
</div>

<style>
  .chat-panel {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }

  .messages-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    padding: 16px;
  }

  .empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    color: var(--text-secondary);
    font-size: 14px;
  }

  .hint {
    margin-top: 8px;
    font-size: 13px;
    color: var(--text-tertiary);
  }

  .editing-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    font-size: 12px;
    color: var(--text-secondary);
  }
</style>
