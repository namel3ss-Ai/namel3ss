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

  function buildSummarySection(title, rows) {
    const section = document.createElement("div");
    section.className = "metric-section";
    const header = document.createElement("div");
    header.className = "metric-section-title";
    header.textContent = title;
    section.appendChild(header);
    if (!rows.length) {
      const empty = document.createElement("div");
      empty.className = "metric-empty";
      empty.textContent = "No data yet.";
      section.appendChild(empty);
      return section;
    }
    rows.forEach((row) => section.appendChild(row));
    return section;
  }

  function buildSummaryRow(label, value) {
    return buildMetricRow({ name: label, value: value }, "counter");
  }

  function buildSummary(summary) {
    if (!summary || typeof summary !== "object") return null;
    const wrapper = document.createElement("div");
    wrapper.className = "panel-stack";
    const health = summary.health || {};
    const healthRows = [
      buildSummaryRow("Total", String(health.total ?? 0)),
      buildSummaryRow("Ok", String(health.ok ?? 0)),
      buildSummaryRow("Blocked", String(health.blocked ?? 0)),
      buildSummaryRow("Failed", String(health.failed ?? 0)),
    ];
    const quality = summary.quality || {};
    const qualityRows = [];
    if (quality.status === "available") {
      const coverage = quality.coverage ?? "n/a";
      const faithfulness = quality.faithfulness ?? "n/a";
      qualityRows.push(buildSummaryRow("Coverage", String(coverage)));
      qualityRows.push(buildSummaryRow("Faithfulness", String(faithfulness)));
    } else {
      qualityRows.push(buildSummaryRow("Status", "Not available"));
    }
    const failures = Array.isArray(summary.failures) ? summary.failures : [];
    const failureRows = failures.map((entry) => {
      const label = entry.category || "unknown";
      const value = String(entry.count ?? 0);
      return buildSummaryRow(label, value);
    });
    if (!failureRows.length) {
      failureRows.push(buildSummaryRow("None", "0"));
    }
    const retries = summary.retries || {};
    const retryReasons = Array.isArray(retries.reasons) ? retries.reasons : [];
    const retryRows = [buildSummaryRow("Total", String(retries.count ?? 0))];
    retryReasons.forEach((entry) => {
      const label = entry.reason || "unspecified";
      const value = String(entry.count ?? 0);
      retryRows.push(buildSummaryRow(label, value));
    });
    wrapper.appendChild(buildSummarySection("Health", healthRows));
    wrapper.appendChild(buildSummarySection("Quality", qualityRows));
    wrapper.appendChild(buildSummarySection("Failures", failureRows));
    wrapper.appendChild(buildSummarySection("Retries", retryRows));
    return wrapper;
  }

  function renderMetrics(input) {
    const container = getContainer();
    if (!container) return;
    const data = input && typeof input === "object"
      ? input
      : (state && typeof state.getCachedMetrics === "function" ? state.getCachedMetrics() : null);
    const counters = Array.isArray(data && data.counters) ? data.counters : [];
    const timings = Array.isArray(data && data.timings) ? data.timings : [];
    const summary = data && typeof data === "object" ? data.summary : null;

    if (!counters.length && !timings.length && !summary) {
      dom.showEmpty(container, "No metrics yet. Run your app.");
      return;
    }

    container.innerHTML = "";
    const summaryBlock = buildSummary(summary);
    if (summaryBlock) {
      container.appendChild(summaryBlock);
    }
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
