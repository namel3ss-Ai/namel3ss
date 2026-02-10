<template>
  <section class="n3-theme-preview" aria-label="Theme preview" role="region">
    <header class="n3-theme-preview-header">
      <h3 class="n3-theme-preview-title">Theme Preview</h3>
      <p class="n3-theme-preview-subtitle">Switch base theme and verify contrast/focus states.</p>
    </header>

    <div class="n3-theme-preview-controls">
      <label class="n3-theme-preview-field">
        <span>Base theme</span>
        <select :value="baseTheme" @change="onThemeChange">
          <option v-for="entry in themes" :key="entry" :value="entry">
            {{ entry }}
          </option>
        </select>
      </label>

      <label class="n3-theme-preview-field">
        <span>Primary color</span>
        <input :value="primaryColor" type="color" @input="onPrimaryChange" />
      </label>

      <label class="n3-theme-preview-field">
        <span>Background color</span>
        <input :value="backgroundColor" type="color" @input="onBackgroundChange" />
      </label>
    </div>

    <div class="n3-theme-preview-surface">
      <button type="button" class="btn primary">Primary Action</button>
      <button type="button" class="btn ghost">Secondary Action</button>
      <a href="#" class="n3-theme-preview-link" @click.prevent>Focusable Link</a>
    </div>
  </section>
</template>

<script>
export default {
  name: "ThemePreview",
  props: {
    baseTheme: {
      type: String,
      default: "default",
    },
    themes: {
      type: Array,
      default: () => ["default", "dark", "high_contrast"],
    },
    primaryColor: {
      type: String,
      default: "#2563EB",
    },
    backgroundColor: {
      type: String,
      default: "#FFFFFF",
    },
  },
  emits: ["change-base-theme", "change-overrides"],
  methods: {
    onThemeChange(event) {
      this.$emit("change-base-theme", String(event.target.value || "default"));
    },
    onPrimaryChange(event) {
      this.$emit("change-overrides", {
        primary_color: String(event.target.value || "#2563EB").toUpperCase(),
      });
    },
    onBackgroundChange(event) {
      this.$emit("change-overrides", {
        background_color: String(event.target.value || "#FFFFFF").toUpperCase(),
      });
    },
  },
};
</script>

<style scoped>
.n3-theme-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--n3-border-color, #d4dbe7);
  border-radius: var(--n3-border-radius, 10px);
  background: var(--n3-surface-raised, #ffffff);
}

.n3-theme-preview-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.n3-theme-preview-title {
  margin: 0;
  font-size: 14px;
}

.n3-theme-preview-subtitle {
  margin: 0;
  color: var(--n3-muted-text-color, #52617d);
  font-size: 12px;
}

.n3-theme-preview-controls {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
}

.n3-theme-preview-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
}

.n3-theme-preview-field select,
.n3-theme-preview-field input {
  padding: 6px 8px;
  border-radius: 8px;
  border: 1px solid var(--n3-border-color, #d4dbe7);
  background: var(--n3-surface-default, #ffffff);
}

.n3-theme-preview-surface {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.n3-theme-preview-link {
  color: var(--n3-primary-color, #2563eb);
}

.n3-theme-preview-surface :focus-visible {
  outline: 2px solid var(--n3-focus-ring, #1f5de1);
  outline-offset: 2px;
}
</style>
