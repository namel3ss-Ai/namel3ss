(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});

  function renderObservabilityPanel(el, handleAction) {
    const panel = el && typeof el === "object" ? el : {};
    const section = document.createElement("section");
    section.className = "ui-element ui-observability-panel";

    const heading = document.createElement("div");
    heading.className = "ui-retrieval-explain-heading";
    heading.textContent = "Observability";
    section.appendChild(heading);

    const explain = resolveExplainPayload(panel);
    if (explain && typeof root.renderRetrievalExplainElement === "function") {
      const explainElement = root.renderRetrievalExplainElement(explain, handleAction);
      section.appendChild(explainElement);
    }

    const tracePanel = resolveTracePanel(panel);
    if (tracePanel && typeof root.renderRetrievalTracePanel === "function") {
      const traceElement = root.renderRetrievalTracePanel(tracePanel);
      section.appendChild(traceElement);
      return section;
    }

    const timeline = buildTimelineRows(explain && explain.retrieval_trace);
    if (!timeline.length) {
      const empty = document.createElement("div");
      empty.className = "ui-retrieval-explain-empty";
      empty.textContent = "Trace timeline unavailable.";
      section.appendChild(empty);
      return section;
    }

    const title = document.createElement("div");
    title.className = "ui-retrieval-explain-trace-title";
    title.textContent = "Trace timeline";
    section.appendChild(title);

    const list = document.createElement("div");
    list.className = "ui-retrieval-explain-trace";
    timeline.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "ui-retrieval-explain-row";

      const rank = document.createElement("span");
      rank.className = "ui-retrieval-explain-rank";
      rank.textContent = `#${entry.rank}`;
      row.appendChild(rank);

      const reason = document.createElement("span");
      reason.className = "ui-retrieval-explain-reason";
      reason.textContent = entry.reason;
      row.appendChild(reason);

      const source = document.createElement("span");
      source.className = "ui-retrieval-explain-source";
      source.textContent = `${entry.document_id || "unknown"} · p${entry.page_number}`;
      row.appendChild(source);

      const chunk = document.createElement("span");
      chunk.className = "ui-retrieval-explain-chunk";
      chunk.textContent = entry.chunk_id;
      row.appendChild(chunk);

      list.appendChild(row);
    });
    section.appendChild(list);
    return section;
  }

  function resolveExplainPayload(panel) {
    if (panel.explain && typeof panel.explain === "object") return panel.explain;
    if (panel.type === "retrieval_explain") return panel;
    return null;
  }

  function resolveTracePanel(panel) {
    if (panel.trace_panel && typeof panel.trace_panel === "object") return panel.trace_panel;
    return null;
  }

  function buildTimelineRows(value) {
    if (!Array.isArray(value)) return [];
    const rows = value
      .filter((entry) => entry && typeof entry === "object")
      .map((entry) => ({
        chunk_id: textValue(entry.chunk_id),
        document_id: textValue(entry.document_id || entry.doc_id || entry.upload_id),
        page_number: positiveInt(entry.page_number, 1),
        rank: positiveInt(entry.rank, 1),
        reason: textValue(entry.reason) || "retrieval",
      }))
      .filter((entry) => entry.chunk_id)
      .sort((left, right) => {
        return (
          left.rank - right.rank ||
          left.document_id.localeCompare(right.document_id) ||
          left.page_number - right.page_number ||
          left.chunk_id.localeCompare(right.chunk_id)
        );
      });
    return rows;
  }

  function positiveInt(value, fallback) {
    const parsed = Number(value);
    if (!Number.isInteger(parsed) || parsed <= 0) return fallback;
    return parsed;
  }

  function textValue(value) {
    return typeof value === "string" ? value.trim() : "";
  }

  root.renderObservabilityPanel = renderObservabilityPanel;
  window.renderObservabilityPanel = renderObservabilityPanel;
})();
