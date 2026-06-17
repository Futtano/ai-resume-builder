/** Chat store — conversation history. */

import type { ApiClient } from "$lib/api/client";
import type { ConversationEntry } from "$lib/api/types";

class ChatStore {
  messages = $state<ConversationEntry[]>([]);
  isLoading = $state(false);
  error = $state<string | null>(null);

  async fetchConversation(api: ApiClient, sessionId: string) {
    this.isLoading = true;
    this.error = null;
    try {
      const res = await api.get<{ conversation: ConversationEntry[] }>(
        `/sessions/${sessionId}/conversation`
      );
      this.messages = res.conversation ?? [];
    } catch (err) {
      this.error = err instanceof Error ? err.message : "Failed to load conversation";
    } finally {
      this.isLoading = false;
    }
  }

  addMessage(entry: ConversationEntry) {
    this.messages = [...this.messages, entry];
  }

  clear() {
    this.messages = [];
  }
}

export const chatStore = new ChatStore();
