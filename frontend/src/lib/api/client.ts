/** Base HTTP client for the Resume Builder API. */

import { auth } from "$lib/stores/auth.svelte";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class ApiClient {
  private base: string = "/api/v1";

  private async request<T>(
    method: string,
    path: string,
    options?: {
      body?: unknown;
      params?: Record<string, string>;
      formData?: FormData;
    }
  ): Promise<T> {
    const url = new URL(`${this.base}${path}`, window.location.origin);
    if (options?.params) {
      Object.entries(options.params).forEach(([k, v]) =>
        url.searchParams.set(k, v)
      );
    }

    const headers: Record<string, string> = {};
    if (options?.body && !options.formData) {
      headers["Content-Type"] = "application/json";
    }

    // Attach auth token if available
    if (auth.accessToken) {
      headers["Authorization"] = `Bearer ${auth.accessToken}`;
    }

    let res = await fetch(url.toString(), {
      method,
      headers,
      body: options?.formData ?? (options?.body ? JSON.stringify(options.body) : undefined),
    });

    // If 401, try refreshing the token once
    if (res.status === 401 && auth.refreshTokenValue) {
      const refreshed = await auth.refreshToken();
      if (refreshed) {
        headers["Authorization"] = `Bearer ${auth.accessToken}`;
        res = await fetch(url.toString(), {
          method,
          headers,
          body: options?.formData ?? (options?.body ? JSON.stringify(options.body) : undefined),
        });
      }
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(
        res.status,
        err.error_code ?? "UNKNOWN",
        err.detail ?? res.statusText
      );
    }

    const ct = res.headers.get("content-type") || "";
    if (ct.includes("octet-stream") || path.endsWith(".docx")) {
      return res.blob() as unknown as T;
    }

    return res.json();
  }

  get<T>(path: string, params?: Record<string, string>) {
    return this.request<T>("GET", path, { params });
  }

  post<T>(path: string, body?: unknown) {
    return this.request<T>("POST", path, { body });
  }

  patch<T>(path: string, body?: unknown) {
    return this.request<T>("PATCH", path, { body });
  }

  delete<T>(path: string) {
    return this.request<T>("DELETE", path);
  }

  upload<T>(path: string, formData: FormData) {
    return this.request<T>("POST", path, { formData });
  }
}
