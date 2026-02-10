<template>
  <section
    class="n3-drawer"
    role="dialog"
    :aria-hidden="open ? 'false' : 'true'"
    :data-open="open ? 'true' : 'false'"
    :data-side="side"
  >
    <header class="n3-drawer-header">
      <slot name="title">Drawer</slot>
      <button type="button" class="n3-drawer-close" aria-label="Close drawer" @click="$emit('close')">Close</button>
    </header>
    <div class="n3-drawer-body">
      <slot />
    </div>
  </section>
</template>

<script>
export default {
  name: "Drawer",
  props: {
    open: {
      type: Boolean,
      default: false,
    },
    side: {
      type: String,
      default: "right",
      validator(value) {
        return value === "left" || value === "right";
      },
    },
  },
  emits: ["close"],
};
</script>

<style scoped>
.n3-drawer {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border: 1px solid #e5e5e5;
  border-radius: 12px;
  background: #fff;
  padding: 12px;
}

.n3-drawer[data-open="false"] {
  display: none;
}

.n3-drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.n3-drawer-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.n3-drawer-close {
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
}
</style>
