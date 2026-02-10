<template>
  <section class="n3-document-library" role="navigation" aria-label="Document library">
    <header class="n3-document-library-header">
      <slot name="title">Documents</slot>
    </header>
    <div
      v-for="doc in documents"
      :key="doc.id"
      class="n3-document-row"
      :data-selected="doc.id === selectedDocumentId ? 'true' : 'false'"
    >
      <button type="button" class="n3-document-select" @click="$emit('select', doc.id)">{{ doc.name }}</button>
      <button type="button" class="n3-document-delete" @click="$emit('delete', doc.id)">Delete</button>
    </div>
  </section>
</template>

<script>
export default {
  name: "DocumentLibrary",
  props: {
    documents: {
      type: Array,
      default: () => [],
    },
    selectedDocumentId: {
      type: String,
      default: null,
    },
  },
  emits: ["select", "delete"],
};
</script>

<style scoped>
.n3-document-library {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.n3-document-library-header {
  font-weight: 600;
}

.n3-document-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.n3-document-select,
.n3-document-delete {
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  background: #fff;
  padding: 6px 8px;
  cursor: pointer;
}

.n3-document-row[data-selected="true"] .n3-document-select {
  border-color: #2563eb;
}
</style>
