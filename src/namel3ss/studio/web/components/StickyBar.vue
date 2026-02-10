<template>
  <div class="n3-sticky-bar" :data-position="position" role="region">
    <slot />
  </div>
</template>

<script>
export default {
  name: "StickyBar",
  props: {
    position: {
      type: String,
      default: "bottom",
      validator(value) {
        return value === "top" || value === "bottom";
      },
    },
  },
};
</script>

<style scoped>
.n3-sticky-bar {
  position: sticky;
  z-index: 5;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(6px);
  border-radius: 10px;
  padding: 8px;
}

.n3-sticky-bar[data-position="bottom"] {
  bottom: 0;
}

.n3-sticky-bar[data-position="top"] {
  top: 0;
}
</style>
