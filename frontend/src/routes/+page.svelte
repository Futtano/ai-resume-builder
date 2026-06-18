<script lang="ts">
  import { goto } from "$app/navigation";
  import { auth } from "$lib/stores/auth.svelte";
  import "../app.css";

  let mode = $state<"login" | "signup">("login");
  let username = $state("");
  let password = $state("");
  let localError = $state<string | null>(null);

  // If already authenticated, go to app
  $effect(() => {
    if (auth.isAuthenticated) {
      goto("/app", { replaceState: true });
    }
  });

  function toggleMode() {
    mode = mode === "login" ? "signup" : "login";
    localError = null;
    auth.clearError();
  }

  async function handleSubmit(e: Event) {
    e.preventDefault();
    localError = null;

    if (!username.trim() || !password.trim()) {
      localError = "Please fill in all fields";
      return;
    }

    const success =
      mode === "login"
        ? await auth.login(username.trim(), password)
        : await auth.register(username.trim(), password);

    if (success) {
      goto("/app", { replaceState: true });
    }
  }

  function getErrorMessage(): string | null {
    return localError ?? auth.error;
  }
</script>

<div class="auth-page">
  <div class="auth-backdrop">
    <div class="auth-glow"></div>
    <div class="auth-gradient-top"></div>
    <div class="auth-gradient-bottom"></div>
  </div>

  <div class="auth-card">
    <!-- Logo / brand -->
    <div class="auth-brand">
      <div class="auth-logo">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
      </div>
      <h1 class="auth-title">Resume Builder</h1>
      <p class="auth-subtitle">
        {mode === "login" ? "Sign in to your account" : "Create your account"}
      </p>
    </div>

    <!-- Form -->
    <form class="auth-form" onsubmit={handleSubmit}>
      <div class="auth-field">
        <label for="username" class="auth-label">Username</label>
        <input
          id="username"
          type="text"
          class="auth-input"
          placeholder="your-username"
          bind:value={username}
          autocomplete={mode === "signup" ? "username" : "username"}
          required
        />
      </div>

      <div class="auth-field">
        <label for="password" class="auth-label">Password</label>
        <input
          id="password"
          type="password"
          class="auth-input"
          placeholder="••••••••"
          bind:value={password}
          autocomplete={mode === "signup" ? "new-password" : "current-password"}
          required
          minlength="8"
        />
      </div>

      {#if getErrorMessage()}
        <div class="auth-error">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="auth-error-icon"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="15" y1="9" x2="9" y2="15" />
            <line x1="9" y1="9" x2="15" y2="15" />
          </svg>
          <span>{getErrorMessage()}</span>
        </div>
      {/if}

      <button type="submit" class="auth-submit" disabled={auth.isLoading}>
        {#if auth.isLoading}
          <svg class="auth-spinner" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" opacity="0.25" />
            <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
          </svg>
          {mode === "login" ? "Signing in..." : "Creating account..."}
        {:else}
          {mode === "login" ? "Sign In" : "Create Account"}
        {/if}
      </button>
    </form>

    <!-- Toggle -->
    <div class="auth-toggle">
      <span class="auth-toggle-text">
        {mode === "login" ? "Don't have an account?" : "Already have an account?"}
      </span>
      <button class="auth-toggle-btn" onclick={toggleMode}>
        {mode === "login" ? "Sign up" : "Sign in"}
      </button>
    </div>
  </div>
</div>

<style>
  /* ── Page layout ── */
  .auth-page {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    background: #0a0a0a;
    position: relative;
    overflow: hidden;
    font-family: "Inter", system-ui, -apple-system, sans-serif;
  }

  /* ── Backdrop effects ── */
  .auth-backdrop {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }

  .auth-glow {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 600px;
    height: 600px;
    background: radial-gradient(
      circle at center,
      rgba(255, 255, 255, 0.06) 0%,
      rgba(255, 255, 255, 0.02) 40%,
      transparent 70%
    );
    border-radius: 50%;
  }

  .auth-gradient-top {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 50%;
    background: linear-gradient(to bottom, #0a0a0a, transparent);
  }

  .auth-gradient-bottom {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 50%;
    background: linear-gradient(to top, #0a0a0a, transparent);
  }

  /* ── Card ── */
  .auth-card {
    position: relative;
    z-index: 1;
    width: 100%;
    max-width: 400px;
    padding: 2.5rem 2rem;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 1rem;
    backdrop-filter: blur(12px);
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  /* ── Brand ── */
  .auth-brand {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
  }

  .auth-logo {
    width: 40px;
    height: 40px;
    color: rgba(255, 255, 255, 0.9);
  }

  .auth-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: #fff;
    letter-spacing: -0.02em;
    margin: 0;
  }

  .auth-subtitle {
    font-size: 0.875rem;
    color: rgba(255, 255, 255, 0.45);
    margin: 0;
  }

  /* ── Form ── */
  .auth-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .auth-field {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
  }

  .auth-label {
    font-size: 0.8125rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.6);
  }

  .auth-input {
    width: 100%;
    padding: 0.625rem 0.875rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.5rem;
    color: #fff;
    font-size: 0.9375rem;
    outline: none;
    transition: border-color 0.2s ease;
    box-sizing: border-box;
  }

  .auth-input::placeholder {
    color: rgba(255, 255, 255, 0.2);
  }

  .auth-input:focus {
    border-color: rgba(255, 255, 255, 0.3);
  }

  /* ── Error ── */
  .auth-error {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.625rem 0.875rem;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: 0.5rem;
    color: #fca5a5;
    font-size: 0.8125rem;
  }

  .auth-error-icon {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
  }

  /* ── Submit button ── */
  .auth-submit {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.75rem 1rem;
    background: #fff;
    color: #0a0a0a;
    border: none;
    border-radius: 0.5rem;
    font-size: 0.9375rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s ease, transform 0.15s ease;
    margin-top: 0.5rem;
  }

  .auth-submit:hover:not(:disabled) {
    opacity: 0.9;
    transform: scale(1.01);
  }

  .auth-submit:active:not(:disabled) {
    transform: scale(0.99);
  }

  .auth-submit:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .auth-spinner {
    width: 18px;
    height: 18px;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  /* ── Toggle ── */
  .auth-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.375rem;
  }

  .auth-toggle-text {
    font-size: 0.8125rem;
    color: rgba(255, 255, 255, 0.4);
  }

  .auth-toggle-btn {
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.8);
    font-size: 0.8125rem;
    font-weight: 500;
    cursor: pointer;
    padding: 0;
    transition: color 0.15s ease;
  }

  .auth-toggle-btn:hover {
    color: #fff;
  }
</style>
