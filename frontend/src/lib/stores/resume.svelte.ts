/** Resume store — working resume state and preview docx blob. */

import type { ApiClient } from "$lib/api/client";
import * as resumeApi from "$lib/api/resume";
import type { ConversationEntry, ParsedResume } from "$lib/api/types";

class ResumeStore {
  workingResume = $state<ParsedResume | null>(null);
  previewDocx = $state<Blob | null>(null);
  isEditing = $state(false);
  editError = $state<string | null>(null);

  async fetchResume(api: ApiClient, sessionId: string) {
    try {
      const res = await resumeApi.getResume(api, sessionId);
      this.workingResume = res.working_resume;
    } catch {
      // Resume may not exist yet — that's fine
    }
  }

  async fetchPreview(api: ApiClient, sessionId: string) {
    try {
      this.previewDocx = await resumeApi.getResumePreview(api, sessionId);
    } catch (err) {
      this.editError = err instanceof Error ? err.message : "Failed to load preview";
    }
  }

  async applyEdit(
    api: ApiClient,
    sessionId: string,
    instruction: string
  ): Promise<ConversationEntry | null> {
    this.isEditing = true;
    this.editError = null;
    try {
      const res = await resumeApi.editResume(api, sessionId, instruction);
      this.workingResume = res.working_resume;
      // Refresh preview after edit
      await this.fetchPreview(api, sessionId);
      return res.conversation_entry;
    } catch (err) {
      this.editError = err instanceof Error ? err.message : "Edit failed";
      return null;
    } finally {
      this.isEditing = false;
    }
  }

  async uploadAndParse(
    api: ApiClient,
    sessionId: string,
    file: File,
    pollTask: (taskId: string) => Promise<unknown>
  ) {
    this.editError = null;
    try {
      await resumeApi.uploadResume(api, sessionId, file);
      const { task_id } = await resumeApi.triggerParse(api, sessionId);
      await pollTask(task_id);
      await this.fetchResume(api, sessionId);
      await this.fetchPreview(api, sessionId);
    } catch (err) {
      this.editError = err instanceof Error ? err.message : "Upload/parse failed";
    }
  }
}

export const resumeStore = new ResumeStore();
