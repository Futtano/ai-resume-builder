<script lang="ts">
  import { goto } from "$app/navigation";

  // Auth is at the root route now — redirect
  $effect(() => {
    goto("/", { replaceState: true });
  });
</script>
