(() => {
  const root = window.N3App || (window.N3App = {});
  const render = root.render || (root.render = {});
  const utils = root.utils;
  const state = root.state;

  const ALLOWED_KINDS = new Set(["short_term", "semantic", "profile"]);
  const SUMMARY_MAX_LENGTH = 160;

  function normalizeText(value, maxLength = SUMMARY_MAX_LENGTH) {
    if (value === undefined || value === null) return "";
    let text = "";
    if (typeof value === "string") {
      text = value;
    } else {
      text = String(value);
    }
    const flattened = text.replace(/\s+/g, " ").trim();
    if (!flattened) return "";
    if (flattened.length <= maxLength) return flattened;
    return `${flattened.slice(0, maxLength)}...`;
  }

  function humanizeReason(reason) {
    if (!reason) return "";
    return String(reason).replace(/_/g, " ").trim();
  }

  function rememberItem(kind, text, reason) {
    const label = ALLOWED_KINDS.has(kind) ? kind : null;
    if (!label) return null;
    const cleaned = normalizeText(text) || "Memory item";
    const because = normalizeText(reason, 120);
    return { kind: label, text: cleaned, because };
  }

  function collectMemoryEvents(tracesList) {
    const recalled = [];
    const written = [];

    function appendItems(target, items, reason) {
      if (!Array.isArray(items)) return;
      items.forEach((item) => {
        if (!item || typeof item !== "object") return;
        const entry = rememberItem(item.kind, item.text, reason);
        if (entry) target.push(entry);
      });
    }

    function visitTrace(trace) {
      if (!trace || typeof trace !== "object") return;
      if (trace.type === "parallel_agents" && Array.isArray(trace.agents)) {
        trace.agents.forEach((agentTrace) => visitTrace(agentTrace));
        return;
      }
      const events = trace.canonical_events;
      if (!Array.isArray(events)) return;
      events.forEach((event) => {
        if (!event || typeof event.type !== "string") return;
        if (event.type === "memory_recall") {
          const query = normalizeText(event.query, 120);
          const reason = query ? `matched "${query}"` : "";
          appendItems(recalled, event.recalled, reason);
        }
        if (event.type === "memory_write") {
          appendItems(written, event.written, humanizeReason(event.reason));
        }
      });
    }

    if (Array.isArray(tracesList)) {
      tracesList.forEach((trace) => visitTrace(trace));
    }
    return { recalled, written };
  }

  function buildSection(title, items, emptyMessage) {
    const section = document.createElement("div");
    section.className = "memory-section";
    const heading = document.createElement("div");
    heading.className = "memory-section-title";
    heading.textContent = title;
    section.appendChild(heading);
    if (!items.length) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = emptyMessage;
      section.appendChild(empty);
      return section;
    }
    const list = document.createElement("div");
    list.className = "list memory-list";
    items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "list-item memory-item";
      const line = document.createElement("div");
      line.className = "memory-line";
      const kind = document.createElement("div");
      kind.className = "memory-kind";
      kind.textContent = item.kind.replace("_", " ");
      const text = document.createElement("div");
      text.className = "memory-text";
      text.textContent = item.text;
      line.appendChild(kind);
      line.appendChild(text);
      row.appendChild(line);
      if (item.because) {
        const because = document.createElement("div");
        because.className = "memory-why";
        because.textContent = `Because: ${item.because}`;
        row.appendChild(because);
      }
      list.appendChild(row);
    });
    section.appendChild(list);
    return section;
  }

  function renderMemoryPanel(data) {
    const panel = document.getElementById("memory");
    if (!panel) return;
    panel.innerHTML = "";
    if (state.getLastRunStatus && state.getLastRunStatus() === "error") {
      utils.showError(panel, state.getLastRunError && state.getLastRunError());
      return;
    }
    const tracesList = Array.isArray(data) ? data : state.getCachedTraces();
    if (!Array.isArray(tracesList) || tracesList.length === 0) {
      utils.showEmpty(panel, "No memory events yet. Run your app.");
      return;
    }
    const memory = collectMemoryEvents(tracesList);
    const wrapper = document.createElement("div");
    wrapper.className = "memory-panel";
    wrapper.appendChild(buildSection("Recalled", memory.recalled, "No memory recalled in this run."));
    wrapper.appendChild(buildSection("Written", memory.written, "No memory written in this run."));
    panel.appendChild(wrapper);
  }

  render.renderMemoryPanel = renderMemoryPanel;
  window.renderMemoryPanel = renderMemoryPanel;
})();
