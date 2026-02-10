<template>
  <label class="n3-locale-selector">
    <span>Locale</span>
    <select :value="locale" @change="onLocaleChange">
      <option v-for="entry in locales" :key="entry" :value="entry">
        {{ entry }}
      </option>
    </select>
  </label>
</template>

<script>
export default {
  name: "LocaleSelector",
  props: {
    locale: {
      type: String,
      default: "en",
    },
    locales: {
      type: Array,
      default: () => ["en"],
    },
  },
  emits: ["change-locale"],
  methods: {
    onLocaleChange(event) {
      this.$emit("change-locale", String(event.target.value || "en"));
    },
  },
};
</script>

<style scoped>
.n3-locale-selector {
  display: inline-flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
}

.n3-locale-selector select {
  min-width: 140px;
  border: 1px solid var(--n3-border-color, #d4dbe7);
  border-radius: 8px;
  padding: 6px 8px;
  background: var(--n3-surface-raised, #fff);
  color: var(--n3-foreground-color, #111827);
}

.n3-locale-selector select:focus-visible {
  outline: 2px solid var(--n3-focus-ring, #1f5de1);
  outline-offset: 2px;
}
</style>
