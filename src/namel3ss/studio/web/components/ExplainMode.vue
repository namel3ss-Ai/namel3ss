<template>
  <section class="n3-explain-mode" role="region" aria-label="Explain mode" :data-visible="visible ? 'true' : 'false'">
    <header class="n3-explain-mode-header">
      <slot name="title">Explain Mode</slot>
    </header>
    <article v-for="entry in entries" :key="entry.chunk_id" class="n3-explain-entry">
      <strong>{{ entry.chunk_id }}</strong>
      <span>score {{ Number(entry.score || 0).toFixed(3) }}</span>
      <span>rerank {{ Number(entry.rerank_score || 0).toFixed(3) }}</span>
      <p v-if="entry.text">{{ entry.text }}</p>
    </article>
  </section>
</template>

<script>
export default {
  name: "ExplainMode",
  props: {
    entries: {
      type: Array,
      default: () => [],
    },
    visible: {
      type: Boolean,
      default: true,
    },
  },
};
</script>

<style scoped>
.n3-explain-mode {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.n3-explain-mode[data-visible="false"] {
  display: none;
}

.n3-explain-mode-header {
  font-weight: 600;
}

.n3-explain-entry {
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.n3-explain-entry p {
  margin: 0;
  color: #444;
}
</style>
