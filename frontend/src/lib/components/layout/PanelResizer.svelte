<script lang="ts">
  let { onResize }: { onResize: (clientX: number) => void } = $props();

  let isDragging = $state(false);

  function handleMouseDown(e: MouseEvent) {
    e.preventDefault();
    isDragging = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    function onMove(ev: MouseEvent) {
      onResize(ev.clientX);
    }

    function onUp() {
      isDragging = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    }

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }

  function handleTouchStart(e: TouchEvent) {
    e.preventDefault();
    isDragging = true;
    document.body.style.userSelect = "none";

    function onMove(ev: TouchEvent) {
      if (ev.touches.length > 0) {
        onResize(ev.touches[0].clientX);
      }
    }

    function onEnd() {
      isDragging = false;
      document.body.style.userSelect = "";
      document.removeEventListener("touchmove", onMove);
      document.removeEventListener("touchend", onEnd);
    }

    document.addEventListener("touchmove", onMove, { passive: false });
    document.addEventListener("touchend", onEnd);
  }
</script>

<button
  class="panel-resizer"
  class:dragging={isDragging}
  aria-label="Resize panels"
  onmousedown={handleMouseDown}
  ontouchstart={handleTouchStart}
></button>
