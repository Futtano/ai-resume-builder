<script lang="ts">
  import { goto } from "$app/navigation";
  import { auth } from "$lib/stores/auth.svelte";
  import LoadingSpinner from "$lib/components/common/LoadingSpinner.svelte";

  let { children } = $props();

  // Redirect to login if not authenticated
  $effect(() => {
    if (!auth.isAuthenticated) {
      goto("/", { replaceState: true });
    }
  });
</script>

{#if auth.isAuthenticated}
  {@render children()}
{:else}
  <div class="auth-guard-loading">
    <LoadingSpinner size={32} />
  </div>
{/if}

<style>
  .auth-guard-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    background: var(--bg-base, #0a0a0a);
  }
</style>
