/** Theme store — light/dark mode with system preference detection. */

class ThemeStore {
  mode = $state<"light" | "dark">("light");

  constructor() {
    const stored = globalThis.localStorage?.getItem("resume_theme");
    if (stored === "light" || stored === "dark") {
      this.mode = stored;
    } else if (globalThis.matchMedia?.("(prefers-color-scheme: dark)").matches) {
      this.mode = "dark";
    }
  }

  /** Call this from a component's $effect to sync the DOM. */
  syncDOM() {
    $effect(() => {
      document.documentElement.dataset.theme = this.mode;
      globalThis.localStorage?.setItem("resume_theme", this.mode);
    });
  }

  toggle() {
    this.mode = this.mode === "light" ? "dark" : "light";
  }
}

export const theme = new ThemeStore();
