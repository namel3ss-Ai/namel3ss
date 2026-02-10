<template>
  <aside class="n3-sidebar" role="complementary" aria-label="Sidebar" :data-collapsed="collapsed ? 'true' : 'false'">
    <slot />
  </aside>
</template>

<script>
export default {
  name: "Sidebar",
  props: {
    collapsed: {
      type: Boolean,
      default: false,
    },
  },
};
</script>

<style scoped>
.n3-sidebar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 220px;
  max-width: 320px;
}

.n3-sidebar[data-collapsed="true"] {
  min-width: 64px;
  max-width: 64px;
  overflow: hidden;
}
</style>
