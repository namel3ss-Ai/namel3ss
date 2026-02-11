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

    const controls = document.createElement("div");
    controls.className = "ui-diagnostics-controls";
    wrapper.appendChild(controls);

    const sortLabel = document.createElement("label");
    sortLabel.className = "ui-diagnostics-control";
    sortLabel.textContent = "Sort by";
    controls.appendChild(sortLabel);

    const sortSelect = document.createElement("select");
    sortSelect.className = "ui-diagnostics-select";
    [
      { value: "severity", label: "severity" },
      { value: "semantic_score", label: "semantic score" },
      { value: "lexical_score", label: "lexical score" },
      { value: "final_score", label: "final score" },
      { value: "doc_id", label: "doc id" },
    ].forEach((entry) => {
      const option = document.createElement("option");
      option.value = entry.value;
      option.textContent = entry.label;
      sortSelect.appendChild(option);
    });
    sortLabel.appendChild(sortSelect);

    const toggles = document.createElement("div");
    toggles.className = "ui-diagnostics-toggles";
    controls.appendChild(toggles);

    const filters = {
      semantic: true,
      lexical: true,
      final: true,
    };
    ["semantic", "lexical", "final"].forEach((mode) => {
      const toggle = document.createElement("label");
      toggle.className = "ui-diagnostics-toggle";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = true;
      input.addEventListener("change", () => {
        filters[mode] = input.checked;
        renderRows();
      });
      toggle.appendChild(input);
      const text = document.createElement("span");
      text.textContent = mode;
      toggle.appendChild(text);
      toggles.appendChild(toggle);
    });

    const list = document.createElement("ul");
    list.className = "ui-diagnostics-list";
    wrapper.appendChild(list);

    const renderRows = () => {
      list.innerHTML = "";
      const sorted = sortEntries(entries, sortSelect.value);
      const visible = sorted.filter((entry) => entryVisible(entry, filters));
      if (!visible.length) {
        const empty = document.createElement("li");
        empty.className = "ui-diagnostics-item ui-diagnostics-filter-empty";
        empty.textContent = "No diagnostics match the selected filters.";
        list.appendChild(empty);
        return;
      }
      visible.forEach((entry) => {
        list.appendChild(renderEntryRow(entry));
      });
    };
    sortSelect.addEventListener("change", renderRows);
    renderRows();
    return wrapper;
  }

  function renderEntryRow(entry) {
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

    const metrics = document.createElement("div");
    metrics.className = "ui-diagnostics-metrics";
    metrics.textContent =
      `doc=${entry.doc_id || "-"} | semantic=${entry.semantic_score.toFixed(4)} | ` +
      `lexical=${entry.lexical_score.toFixed(4)} | final=${entry.final_score.toFixed(4)}`;
    item.appendChild(metrics);

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
    return item;
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
      const row = {
        severity: severity,
        category: category,
        message: message,
        hint: textValue(entry.hint),
        source: textValue(entry.source),
        stable_code: textValue(entry.stable_code),
        semantic_score: toScore(entry.semantic_score),
        lexical_score: toScore(entry.lexical_score),
        final_score: toScore(entry.final_score),
        doc_id: textValue(entry.doc_id),
        modes: inferModes(entry),
      };
      rows.push(row);
    });
    rows.sort((a, b) => fallbackSort(a, b));
    return rows;
  }

  function inferModes(entry) {
    const modes = new Set();
    const explicitModes = Array.isArray(entry.modes) ? entry.modes : [];
    explicitModes.forEach((item) => {
      const text = textValue(item).toLowerCase();
      if (text === "semantic" || text === "lexical" || text === "final") modes.add(text);
    });
    const category = textValue(entry.category).toLowerCase();
    if (category.includes("semantic")) modes.add("semantic");
    if (category.includes("lexical")) modes.add("lexical");
    if (category.includes("final")) modes.add("final");
    if (toScore(entry.semantic_score) > 0) modes.add("semantic");
    if (toScore(entry.lexical_score) > 0) modes.add("lexical");
    if (toScore(entry.final_score) > 0) modes.add("final");
    if (!modes.size) {
      modes.add("semantic");
      modes.add("lexical");
      modes.add("final");
    }
    return {
      semantic: modes.has("semantic"),
      lexical: modes.has("lexical"),
      final: modes.has("final"),
    };
  }

  function entryVisible(entry, filters) {
    if (filters.semantic && entry.modes.semantic) return true;
    if (filters.lexical && entry.modes.lexical) return true;
    if (filters.final && entry.modes.final) return true;
    return false;
  }

  function sortEntries(entries, sortBy) {
    const sorted = entries.slice();
    if (sortBy === "semantic_score") {
      sorted.sort((a, b) => compareScoreOrdering(a, b, ["semantic_score", "final_score", "lexical_score"]));
      return sorted;
    }
    if (sortBy === "lexical_score") {
      sorted.sort((a, b) => compareScoreOrdering(a, b, ["lexical_score", "final_score", "semantic_score"]));
      return sorted;
    }
    if (sortBy === "final_score") {
      sorted.sort((a, b) => compareScoreOrdering(a, b, ["final_score", "semantic_score", "lexical_score"]));
      return sorted;
    }
    if (sortBy === "doc_id") {
      sorted.sort((a, b) => a.doc_id.localeCompare(b.doc_id) || compareScoreOrdering(a, b, ["final_score", "semantic_score", "lexical_score"]));
      return sorted;
    }
    sorted.sort((a, b) => fallbackSort(a, b));
    return sorted;
  }

  function compareScoreOrdering(a, b, scoreOrder) {
    const keys = Array.isArray(scoreOrder) ? scoreOrder : [];
    for (const key of keys) {
      const delta = Number(b[key]) - Number(a[key]);
      if (Math.abs(delta) > 0.0000001) return delta;
    }
    return tieBreakSort(a, b);
  }

  function fallbackSort(a, b) {
    return (
      severityRank(a.severity) - severityRank(b.severity) ||
      tieBreakSort(a, b)
    );
  }

  function tieBreakSort(a, b) {
    return (
      a.doc_id.localeCompare(b.doc_id) ||
      a.category.localeCompare(b.category) ||
      a.stable_code.localeCompare(b.stable_code) ||
      a.message.localeCompare(b.message)
    );
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

  function toScore(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return 0;
    if (number < 0) return 0;
    if (number > 1) return 1;
    return Math.round(number * 10000) / 10000;
  }

  function textValue(value) {
    return typeof value === "string" ? value.trim() : "";
  }

  root.renderDiagnosticsElement = renderDiagnosticsElement;
  window.renderDiagnosticsElement = renderDiagnosticsElement;
})();
