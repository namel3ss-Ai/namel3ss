<template>
  <section class="n3-plugin-manager" role="region" aria-label="Plugin manager">
    <header class="n3-plugin-manager-header">
      <h3>Plugin Manager</h3>
      <p>Enable or disable plugins in deterministic order.</p>
    </header>
    <ul class="n3-plugin-manager-list">
      <li v-for="plugin in orderedPlugins" :key="plugin.name" class="n3-plugin-row">
        <div class="n3-plugin-meta">
          <div class="n3-plugin-name">{{ plugin.name }}</div>
          <div class="n3-plugin-version">v{{ plugin.version || "0.1.0" }}</div>
        </div>
        <label class="n3-plugin-toggle">
          <input
            type="checkbox"
            :checked="isEnabled(plugin.name)"
            @change="togglePlugin(plugin.name, $event.target.checked)"
          />
          <span>{{ isEnabled(plugin.name) ? "Enabled" : "Disabled" }}</span>
        </label>
      </li>
    </ul>
  </section>
</template>

<script>
export default {
  name: "PluginManager",
  props: {
    plugins: {
      type: Array,
      default: () => [],
    },
    enabledPlugins: {
      type: Array,
      default: () => [],
    },
  },
  emits: ["toggle-plugin"],
  computed: {
    orderedPlugins() {
      return [...this.plugins].sort((a, b) => String(a.name || "").localeCompare(String(b.name || "")));
    },
  },
  methods: {
    isEnabled(name) {
      return this.enabledPlugins.includes(name);
    },
    togglePlugin(name, enabled) {
      this.$emit("toggle-plugin", { name, enabled: Boolean(enabled) });
    },
  },
};
</script>

<style scoped>
.n3-plugin-manager {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--n3-border-color, #d4dbe7);
  border-radius: var(--n3-border-radius, 10px);
  background: var(--n3-surface-raised, #fff);
}

.n3-plugin-manager-header h3 {
  margin: 0;
  font-size: 14px;
}

.n3-plugin-manager-header p {
  margin: 2px 0 0;
  color: var(--n3-muted-text-color, #52617d);
  font-size: 12px;
}

.n3-plugin-manager-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.n3-plugin-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border: 1px solid var(--n3-border-color, #d4dbe7);
  border-radius: 8px;
  padding: 8px;
}

.n3-plugin-name {
  font-weight: 600;
}

.n3-plugin-version {
  font-size: 12px;
  color: var(--n3-muted-text-color, #52617d);
}

.n3-plugin-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}
</style>
