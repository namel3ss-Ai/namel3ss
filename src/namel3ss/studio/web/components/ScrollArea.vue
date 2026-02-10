<template>
  <div class="n3-scroll-area" :data-axis="axis" role="region">
    <slot />
  </div>
</template>

<script>
export default {
  name: "ScrollArea",
  props: {
    axis: {
      type: String,
      default: "vertical",
      validator(value) {
        return value === "vertical" || value === "horizontal";
      },
    },
  },
};
</script>

<style scoped>
.n3-scroll-area {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}

.n3-scroll-area[data-axis="horizontal"] {
  flex-direction: row;
  overflow-x: auto;
  overflow-y: hidden;
}
</style>
