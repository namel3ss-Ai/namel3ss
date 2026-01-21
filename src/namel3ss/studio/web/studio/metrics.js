(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const dom = root.dom;
  const net = root.net;
  const metrics = root.metrics || (root.metrics = {});

  function getContainer() {
    return document.getElementById("metrics");
  }

  function formatLabels(labels) {
    if (!labels || typeof labels !== "object") return "";
    const keys = Object.keys(labels).sort();
    if (!keys.length) return "";
    return keys.map((key) => `${key}=${labels[key]}`).join(", ");
  }

  function buildMetricRow(entry, kind) {
    const row = document.createElement("div");
    row.className = "metric-row";

    const meta = document.createElement("div");
    meta.className = "metric-meta";

    const name = document.createElement("div");
    name.className = "metric-name";
    name.textContent = entry.name || kind;

    const labels = document.createElement("div");
    labels.className = "metric-labels";
    labels.textContent = formatLabels(entry.labels);

    meta.appendChild(name);
    if (labels.textContent) meta.appendChild(labels);

    const value = document.createElement("div");
    value.className = "metric-value";
    if (kind === "timing") {
      const count = entry.count ?? 0;
      const total = entry.total_steps ?? 0;
      const min = entry.min_steps ?? 0;
      const max = entry.max_steps ?? 0;
      const last = entry.last_steps ?? 0;
      value.textContent = `count ${count} | total ${total} | min ${min} | max ${max} | last ${last}`;
    } else {
      value.textContent = String(entry.value ?? 0);
    }

    row.appendChild(meta);
    row.appendChild(value);
    return row;
  }

  function buildSection(title, entries, kind) {
    const section = document.createElement("div");
    section.className = "metric-section";

    const header = document.createElement("div");
    header.className = "metric-section-title";
    header.textContent = title;
    section.appendChild(header);

    if (!entries.length) {
      const empty = document.createElement("div");
      empty.className = "metric-empty";
      empty.textContent = `No ${title.toLowerCase()} yet.`;
      section.appendChild(empty);
      return section;
    }

    entries.forEach((entry) => {
      if (!entry || typeof entry !== "object") return;
      section.appendChild(buildMetricRow(entry, kind));
    });
    return section;
  }

  function renderMetrics(input) {
    const container = getContainer();
    if (!container) return;
    const data = input && typeof input === "object"
      ? input
      : (state && typeof state.getCachedMetrics === "function" ? state.getCachedMetrics() : null);
    const counters = Array.isArray(data && data.counters) ? data.counters : [];
    const timings = Array.isArray(data && data.timings) ? data.timings : [];

    if (!counters.length && !timings.length) {
      dom.showEmpty(container, "No metrics yet. Run your app.");
      return;
    }

    container.innerHTML = "";
    container.appendChild(buildSection("Counters", counters, "counter"));
    container.appendChild(buildSection("Timings", timings, "timing"));
  }

  async function refreshMetrics() {
    if (!net || typeof net.fetchJson !== "function") return;
    try {
      const payload = await net.fetchJson("/api/metrics");
      if (state && typeof state.setCachedMetrics === "function") {
        state.setCachedMetrics(payload);
      }
      renderMetrics(payload);
    } catch (_err) {
      renderMetrics(null);
    }
  }

  metrics.renderMetrics = renderMetrics;
  metrics.refreshMetrics = refreshMetrics;
  window.renderMetrics = renderMetrics;
})();
