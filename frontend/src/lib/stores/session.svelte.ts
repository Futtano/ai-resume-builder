/** Session store — manages the list of sessions and the active session. */

import type { ApiClient } from "$lib/api/client";
import * as sessionsApi from "$lib/api/sessions";
import type { SessionSummary } from "$lib/api/types";

class SessionStore {
  list = $state<SessionSummary[]>([]);
  currentId = $state<string | null>(null);
  total = $state(0);
  isLoading = $state(false);
  error = $state<string | null>(null);

  current = $derived(
    this.list.find((s) => s.session_id === this.currentId) ?? null
  );

  async fetchSessions(api: ApiClient) {
    this.isLoading = true;
    this.error = null;
    try {
      const res = await sessionsApi.listSessions(api);
      this.list = res.items;
      this.total = res.total;
    } catch (err) {
      this.error = err instanceof Error ? err.message : "Failed to load sessions";
    } finally {
      this.isLoading = false;
    }
  }

  async createSession(api: ApiClient): Promise<string | null> {
    this.error = null;
    try {
      const res = await sessionsApi.createSession(api);
      await this.fetchSessions(api);
      this.currentId = res.session_id;
      return res.session_id;
    } catch (err) {
      this.error = err instanceof Error ? err.message : "Failed to create session";
      return null;
    }
  }

  async deleteSession(api: ApiClient, id: string) {
    this.error = null;
    try {
      await sessionsApi.deleteSession(api, id);
      if (this.currentId === id) {
        this.currentId = null;
      }
      await this.fetchSessions(api);
    } catch (err) {
      this.error = err instanceof Error ? err.message : "Failed to delete session";
    }
  }

  selectSession(id: string) {
    this.currentId = id;
  }
}

export const sessionStore = new SessionStore();
