<script lang="ts">
  import { theme } from "$lib/stores/theme.svelte";

  type ToggleSize = "sm" | "md" | "lg";

  let {
    class: className = "",
    size = "md" as ToggleSize,
  }: { class?: string; size?: ToggleSize } = $props();

  const sizeConfig = {
    sm: { track: "h-6 w-11", knob: "h-4 w-4", icon: 12, offset: "calc(100% - 1.125rem)" },
    md: { track: "h-8 w-14", knob: "h-6 w-6", icon: 16, offset: "calc(100% - 1.625rem)" },
    lg: { track: "h-10 w-[4.5rem]", knob: "h-8 w-8", icon: 20, offset: "calc(100% - 2.125rem)" },
  } as const;

  let config = $derived(sizeConfig[size]);
  let isDark = $derived(theme.mode === "dark");
  let knobLeft = $derived(isDark ? config.offset : "0.125rem");

  function toggle() {
    theme.toggle();
  }
</script>

<button
  class="theme-toggle {config.track} {className}"
  class:dark={isDark}
  style="border-color: {isDark ? '#2d2a4e' : '#e8d5b7'}; background-color: {isDark ? '#1a1838' : '#fef3c7'};"
  onclick={toggle}
  type="button"
  aria-label="Toggle theme"
>
  <div
    class="knob {config.knob}"
    style="left: {knobLeft}; background-color: {isDark ? '#e8e6f0' : '#ff9500'}; color: {isDark ? '#1a1838' : 'white'};"
  >
    <!-- Sun icon -->
    <svg
      class="icon icon-sun"
      aria-hidden="true"
      fill="none"
      height={config.icon}
      viewBox="0 0 24 24"
      width={config.icon}
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle cx="12" cy="12" fill="currentColor" r="3.25" />
      <g stroke="currentColor" stroke-linecap="round" stroke-width="2">
        <path d="M12 2.5v2.5" />
        <path d="M12 19v2.5" />
        <path d="M4.22 4.22l1.77 1.77" />
        <path d="M18.01 18.01l1.77 1.77" />
        <path d="M2.5 12h2.5" />
        <path d="M19 12h2.5" />
        <path d="M4.22 19.78l1.77-1.77" />
        <path d="M18.01 5.99l1.77-1.77" />
      </g>
    </svg>
    <!-- Moon icon -->
    <svg
      class="icon icon-moon"
      aria-hidden="true"
      fill="none"
      height={config.icon}
      viewBox="0 0 24 24"
      width={config.icon}
      xmlns="http://www.w3.org/2000/svg"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  </div>
</button>

<style>
  .theme-toggle {
    position: relative;
    border-radius: 9999px;
    border-width: 2px;
    cursor: pointer;
    transition: background-color 0.7s cubic-bezier(0.68, -0.55, 0.265, 1.55),
      border-color 0.7s cubic-bezier(0.68, -0.55, 0.265, 1.55);
  }

  .knob {
    position: absolute;
    top: 50%;
    display: grid;
    place-items: center;
    border-radius: 9999px;
    transform: translateY(-50%);
    transition: left 0.7s cubic-bezier(0.68, -0.55, 0.265, 1.55),
      background-color 0.7s cubic-bezier(0.68, -0.55, 0.265, 1.55);
  }

  .icon {
    display: block;
    flex-shrink: 0;
    grid-column: 1;
    grid-row: 1;
    transform-origin: center;
    transition: all 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55);
  }

  .icon-sun {
    rotate: 0deg;
    scale: 1;
    opacity: 1;
  }

  .theme-toggle.dark .icon-sun {
    rotate: 90deg;
    scale: 0.5;
    opacity: 0;
  }

  .icon-moon {
    rotate: -90deg;
    scale: 0.5;
    opacity: 0;
  }

  .theme-toggle.dark .icon-moon {
    rotate: 0deg;
    scale: 1;
    opacity: 1;
  }
</style>
