<template>
  <section class="n3-citation-panel" role="complementary" aria-label="Citation panel">
    <header class="n3-citation-panel-header">
      <slot name="title">Citations</slot>
    </header>
    <button
      v-for="citation in citations"
      :key="citation.id"
      type="button"
      class="n3-citation-item"
      :data-selected="citation.id === selectedId ? 'true' : 'false'"
      @click="$emit('select', citation.id)"
    >
      <strong>{{ citation.title }}</strong>
      <span v-if="citation.snippet" class="n3-citation-snippet">{{ citation.snippet }}</span>
      <span v-if="citation.page !== null && citation.page !== undefined" class="n3-citation-page">p. {{ citation.page }}</span>
    </button>
  </section>
</template>

<script>
export default {
  name: "CitationPanel",
  props: {
    citations: {
      type: Array,
      default: () => [],
    },
    selectedId: {
      type: String,
      default: null,
    },
  },
  emits: ["select"],
};
</script>

<style scoped>
.n3-citation-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.n3-citation-panel-header {
  font-weight: 600;
}

.n3-citation-item {
  text-align: left;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  background: #fff;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  cursor: pointer;
}

.n3-citation-item[data-selected="true"] {
  border-color: #2563eb;
}

.n3-citation-snippet {
  color: #555;
  font-size: 12px;
}

.n3-citation-page {
  color: #333;
  font-size: 12px;
}
</style>
