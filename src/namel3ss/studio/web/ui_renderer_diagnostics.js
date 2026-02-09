(function () {
  const root = window.N3UIRender || (window.N3UIRender = {});

  function renderDiagnosticsElement(el) {
    const wrapper = document.createElement("section");
    wrapper.className = "ui-element ui-diagnostics-panel";

    const heading = document.createElement("h3");
    heading.className = "ui-diagnostics-heading";
    heading.textContent = "Unified Diagnostics";
    wrapper.appendChild(heading);

    const entries = normalizeEntries(el && el.entries);
    if (!entries.length) {
      const empty = document.createElement("div");
      empty.className = "ui-diagnostics-empty";
      empty.textContent = "No diagnostics found.";
      wrapper.appendChild(empty);
      return wrapper;
    }

    const list = document.createElement("ul");
    list.className = "ui-diagnostics-list";
    entries.forEach((entry) => {
      const item = document.createElement("li");
      item.className = `ui-diagnostics-item severity-${entry.severity}`;

      const top = document.createElement("div");
      top.className = "ui-diagnostics-item-top";
      const badge = document.createElement("span");
      badge.className = `ui-diagnostics-badge severity-${entry.severity}`;
      badge.textContent = entry.severity;
      top.appendChild(badge);
      const code = document.createElement("span");
      code.className = "ui-diagnostics-code";
      code.textContent = entry.stable_code || entry.category;
      top.appendChild(code);
      item.appendChild(top);

      const message = document.createElement("div");
      message.className = "ui-diagnostics-message";
      message.textContent = entry.message;
      item.appendChild(message);

      if (entry.hint) {
        const hint = document.createElement("div");
        hint.className = "ui-diagnostics-hint";
        hint.textContent = entry.hint;
        item.appendChild(hint);
      }
      if (entry.source) {
        const source = document.createElement("div");
        source.className = "ui-diagnostics-source";
        source.textContent = entry.source;
        item.appendChild(source);
      }

      list.appendChild(item);
    });
    wrapper.appendChild(list);
    return wrapper;
  }

  function normalizeEntries(value) {
    if (!Array.isArray(value)) return [];
    const rows = [];
    value.forEach((entry) => {
      if (!entry || typeof entry !== "object") return;
      const severity = normalizeSeverity(entry.severity);
      const category = textValue(entry.category) || "diagnostic";
      const message = textValue(entry.message);
      if (!message) return;
      rows.push({
        severity: severity,
        category: category,
        message: message,
        hint: textValue(entry.hint),
        source: textValue(entry.source),
        stable_code: textValue(entry.stable_code),
      });
    });
    rows.sort((a, b) => severityRank(a.severity) - severityRank(b.severity) || a.category.localeCompare(b.category) || a.message.localeCompare(b.message));
    return rows;
  }

  function normalizeSeverity(value) {
    const text = textValue(value).toLowerCase();
    if (text === "error" || text === "warn" || text === "info") return text;
    return "info";
  }

  function severityRank(value) {
    if (value === "error") return 0;
    if (value === "warn") return 1;
    return 2;
  }

  function textValue(value) {
    return typeof value === "string" ? value.trim() : "";
  }

  root.renderDiagnosticsElement = renderDiagnosticsElement;
  window.renderDiagnosticsElement = renderDiagnosticsElement;
})();
