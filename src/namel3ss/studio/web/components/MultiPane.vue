<template>
  <div class="n3-multi-pane" :data-mode="mode">
    <section class="n3-multi-pane-left">
      <slot name="left" />
    </section>
    <section class="n3-multi-pane-center">
      <slot name="center" />
    </section>
    <section v-if="mode === 'three'" class="n3-multi-pane-right">
      <slot name="right" />
    </section>
  </div>
</template>

<script>
export default {
  name: "MultiPane",
  props: {
    mode: {
      type: String,
      default: "two",
      validator(value) {
        return value === "two" || value === "three";
      },
    },
  },
};
</script>

<style scoped>
.n3-multi-pane {
  display: grid;
  gap: 12px;
  align-items: start;
}

.n3-multi-pane[data-mode="two"] {
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
}

.n3-multi-pane[data-mode="three"] {
  grid-template-columns: minmax(180px, 1fr) minmax(0, 2fr) minmax(180px, 1fr);
}

.n3-multi-pane-left,
.n3-multi-pane-center,
.n3-multi-pane-right {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}
</style>
