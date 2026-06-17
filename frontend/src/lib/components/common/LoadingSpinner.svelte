<script lang="ts">
  let { size = 20 }: { size?: number } = $props();
</script>

<svg
  class="spinner"
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill="none"
  xmlns="http://www.w3.org/2000/svg"
>
  <circle cx="12" cy="12" r="10" stroke="var(--border-default)" stroke-width="2" />
  <path
    d="M12 2a10 10 0 0 1 10 10"
    stroke="var(--accent)"
    stroke-width="2"
    stroke-linecap="round"
  >
    <animateTransform
      attributeName="transform"
      type="rotate"
      from="0 12 12"
      to="360 12 12"
      dur="0.8s"
      repeatCount="indefinite"
    />
  </path>
</svg>

<style>
  .spinner {
    display: block;
    flex-shrink: 0;
  }
</style>
