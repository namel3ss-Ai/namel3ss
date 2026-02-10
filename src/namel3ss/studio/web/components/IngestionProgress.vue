<template>
  <section class="n3-ingestion-progress" role="status" aria-live="polite">
    <header class="n3-ingestion-progress-header">
      <slot name="title">Ingestion Progress</slot>
    </header>
    <div class="n3-ingestion-progress-body">
      <div class="n3-ingestion-status">{{ status }}</div>
      <progress class="n3-ingestion-meter" :value="percent" max="100">{{ percent }}%</progress>
      <div class="n3-ingestion-percent">{{ percent }}%</div>
      <ul v-if="errors && errors.length" class="n3-ingestion-errors">
        <li v-for="(error, index) in errors" :key="index">{{ error }}</li>
      </ul>
    </div>
    <button type="button" class="n3-ingestion-retry" @click="$emit('retry')">Retry</button>
  </section>
</template>

<script>
export default {
  name: "IngestionProgress",
  props: {
    status: {
      type: String,
      default: "idle",
    },
    percent: {
      type: Number,
      default: 0,
    },
    errors: {
      type: Array,
      default: () => [],
    },
  },
  emits: ["retry"],
};
</script>

<style scoped>
.n3-ingestion-progress {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.n3-ingestion-progress-header {
  font-weight: 600;
}

.n3-ingestion-progress-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.n3-ingestion-errors {
  margin: 0;
  padding-left: 18px;
  color: #991b1b;
}

.n3-ingestion-retry {
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  background: #fff;
  padding: 6px 10px;
  cursor: pointer;
}
</style>
