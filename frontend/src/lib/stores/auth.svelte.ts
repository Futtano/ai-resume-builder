/** Auth store — token management, login, register, logout. */

import { browser } from "$app/environment";

const STORAGE_KEY = "resume_auth";

interface StoredAuth {
  accessToken: string;
  refreshToken: string;
  userId: string;
  username: string;
}

function loadFromStorage(): StoredAuth | null {
  if (!browser) return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as StoredAuth;
  } catch {
    return null;
  }
}

function saveToStorage(auth: StoredAuth) {
  if (!browser) return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(auth));
}

function clearStorage() {
  if (!browser) return;
  localStorage.removeItem(STORAGE_KEY);
}

// ── Singleton state ──

const stored = loadFromStorage();

let _accessToken = $state(stored?.accessToken ?? "");
let _refreshToken = $state(stored?.refreshToken ?? "");
let _userId = $state(stored?.userId ?? "");
let _username = $state(stored?.username ?? "");
let _isLoading = $state(false);
let _error = $state<string | null>(null);

// Derived
const isAuthenticated = $derived(!!_accessToken);

function _persist() {
  saveToStorage({
    accessToken: _accessToken,
    refreshToken: _refreshToken,
    userId: _userId,
    username: _username,
  });
}

async function login(username: string, password: string): Promise<boolean> {
  _isLoading = true;
  _error = null;

  try {
    const formData = new URLSearchParams();
    formData.set("username", username);
    formData.set("password", password);

    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      _error = err.detail ?? "Invalid username or password";
      return false;
    }

    const data = await res.json();
    _accessToken = data.access_token;
    _refreshToken = data.refresh_token;

    // Decode JWT to get user info (no network call needed)
    const payload = JSON.parse(atob(data.access_token.split(".")[1]));
    _userId = payload.sub;
    _username = payload.username;

    _persist();
    return true;
  } catch (e) {
    _error = e instanceof Error ? e.message : "Network error";
    return false;
  } finally {
    _isLoading = false;
  }
}

async function register(
  username: string,
  password: string
): Promise<boolean> {
  _isLoading = true;
  _error = null;

  try {
    const res = await fetch("/api/v1/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Registration failed" }));
      _error = err.detail ?? "Could not create account";
      return false;
    }

    const data = await res.json();
    _accessToken = data.access_token;
    _refreshToken = data.refresh_token;

    const payload = JSON.parse(atob(data.access_token.split(".")[1]));
    _userId = payload.sub;
    _username = payload.username;

    _persist();
    return true;
  } catch (e) {
    _error = e instanceof Error ? e.message : "Network error";
    return false;
  } finally {
    _isLoading = false;
  }
}

async function doRefreshToken(): Promise<boolean> {
  if (!_refreshToken) return false;

  try {
    const res = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: _refreshToken }),
    });

    if (!res.ok) {
      logout();
      return false;
    }

    const data = await res.json();
    _accessToken = data.access_token;
    _refreshToken = data.refresh_token;

    const payload = JSON.parse(atob(data.access_token.split(".")[1]));
    _userId = payload.sub;
    _username = payload.username;

    _persist();
    return true;
  } catch {
    logout();
    return false;
  }
}

function logout() {
  _accessToken = "";
  _refreshToken = "";
  _userId = "";
  _username = "";
  _error = null;
  clearStorage();
}

function clearError() {
  _error = null;
}

export const auth = {
  get accessToken() { return _accessToken; },
  get refreshTokenValue() { return _refreshToken; },
  get userId() { return _userId; },
  get username() { return _username; },
  get isLoading() { return _isLoading; },
  get error() { return _error; },
  get isAuthenticated() { return isAuthenticated; },
  login,
  register,
  refreshToken: doRefreshToken,
  logout,
  clearError,
};
