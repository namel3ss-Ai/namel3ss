(function () {
  const root = window.N3UIRender || (window.N3UIRender = {});

  function renderRetrievalTracePanel(panel) {
    const section = document.createElement("section");
    section.className = "ui-element ui-retrieval-trace-panel";

    const heading = document.createElement("h3");
    heading.className = "ui-diagnostics-heading";
    heading.textContent = "Retrieval Trace";
    section.appendChild(heading);

    if (!panel || typeof panel !== "object") {
      section.appendChild(emptyRow("Trace is unavailable."));
      return section;
    }

    if (panel.enabled === false) {
      const warning = textValue(panel.warning) || "Retrieval trace diagnostics are disabled.";
      section.appendChild(emptyRow(warning));
      return section;
    }

    if (panel.available !== true) {
      section.appendChild(emptyRow("No retrieval trace captured for the latest run."));
      return section;
    }

    const trace = panel.trace && typeof panel.trace === "object" ? panel.trace : {};
    const query = textValue(trace.query) || "(empty)";
    const tieBreaker = textValue(trace.tie_breaker) || "";
    const params = trace.params && typeof trace.params === "object" ? trace.params : {};

    const meta = document.createElement("div");
    meta.className = "ui-diagnostics-metrics";
    meta.textContent = `query=${query}`;
    section.appendChild(meta);

    if (tieBreaker) {
      const tie = document.createElement("div");
      tie.className = "ui-diagnostics-hint";
      tie.textContent = `tie_breaker=${tieBreaker}`;
      section.appendChild(tie);
    }

    section.appendChild(renderParamList(params));
    section.appendChild(renderRowsTable("Trace Final Ranking", trace.final));

    const simulated = panel.what_if && typeof panel.what_if === "object" ? panel.what_if : {};
    const simulatedRows = Array.isArray(simulated.final) ? simulated.final : [];
    section.appendChild(renderRowsTable("What-If Simulation", simulatedRows));
    return section;
  }

  function renderParamList(params) {
    const block = document.createElement("div");
    block.className = "list";
    const orderedKeys = ["semantic_weight", "semantic_k", "lexical_k", "final_top_k"];
    let count = 0;
    orderedKeys.forEach((key) => {
      if (!(key in params)) return;
      const value = params[key];
      const row = document.createElement("div");
      row.className = "list-item";
      row.textContent = `${key}: ${formatValue(value)}`;
      block.appendChild(row);
      count += 1;
    });
    if (!count) {
      block.appendChild(emptyRow("No trace parameters available."));
    }
    return block;
  }

  function renderRowsTable(title, rows) {
    const block = document.createElement("div");
    block.className = "data-section";

    const titleNode = document.createElement("div");
    titleNode.className = "data-title";
    titleNode.textContent = title;
    block.appendChild(titleNode);

    const list = document.createElement("div");
    list.className = "list";
    const normalized = normalizeRows(rows);
    if (!normalized.length) {
      list.appendChild(emptyRow("No rows."));
      block.appendChild(list);
      return block;
    }
    normalized.forEach((row) => {
      const item = document.createElement("div");
      item.className = "list-item";
      item.textContent =
        `${row.doc_id} | final=${row.final_score.toFixed(4)} | ` +
        `semantic=${row.semantic_score.toFixed(4)} | lexical=${row.lexical_score.toFixed(4)}`;
      list.appendChild(item);
    });
    block.appendChild(list);
    return block;
  }

  function normalizeRows(value) {
    if (!Array.isArray(value)) return [];
    const rows = [];
    value.forEach((entry) => {
      if (!entry || typeof entry !== "object") return;
      const docId = textValue(entry.doc_id);
      if (!docId) return;
      rows.push({
        doc_id: docId,
        semantic_score: toScore(entry.semantic_score),
        lexical_score: toScore(entry.lexical_score),
        final_score: toScore(entry.final_score),
      });
    });
    rows.sort((a, b) => {
      return (
        b.final_score - a.final_score ||
        b.semantic_score - a.semantic_score ||
        b.lexical_score - a.lexical_score ||
        a.doc_id.localeCompare(b.doc_id)
      );
    });
    return rows;
  }

  function emptyRow(message) {
    const node = document.createElement("div");
    node.className = "ui-diagnostics-empty";
    node.textContent = message;
    return node;
  }

  function formatValue(value) {
    if (typeof value === "number") {
      return Number.isInteger(value) ? String(value) : value.toFixed(4);
    }
    if (typeof value === "string") return value;
    if (value === null || typeof value === "undefined") return "null";
    return JSON.stringify(value);
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

  root.renderRetrievalTracePanel = renderRetrievalTracePanel;
  window.renderRetrievalTracePanel = renderRetrievalTracePanel;
})();
