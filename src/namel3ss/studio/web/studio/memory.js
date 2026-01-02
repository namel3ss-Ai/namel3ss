(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const dom = root.dom;
  const memory = root.memory || (root.memory = {});

  function formatText(value) {
    if (value === null || value === undefined) return "";
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    try {
      return JSON.stringify(value, null, 2);
    } catch (err) {
      return String(value);
    }
  }

  function collectMemoryEntries(traces) {
    const entries = [];
    (traces || []).forEach((trace) => {
      if (!trace) return;
      const type = typeof trace.type === "string" ? trace.type : "";
      const isMemory = type.includes("memory");
      const detail =
        trace.title || trace.message || trace.output || trace.result || trace.summary || trace.lines || "";
      if (isMemory) {
        entries.push({
          kind: type || "memory",
          text: formatText(detail) || "Memory event captured.",
        });
      }
      if (trace.memory) {
        entries.push({
          kind: "memory",
          text: formatText(trace.memory),
        });
      }
      if (Array.isArray(trace.memory_events)) {
        trace.memory_events.forEach((event) => {
          entries.push({
            kind: event && event.type ? event.type : "memory",
            text: formatText(event && (event.message || event.summary || event.detail)) || "Memory event captured.",
          });
        });
      }
    });
    return entries.filter((entry) => entry.text).slice(0, 10);
  }

  function renderMemory(nextTraces) {
    const panel = document.getElementById("memory");
    if (!panel) return;
    const tracesList = Array.isArray(nextTraces) ? nextTraces : state.getCachedTraces();
    panel.innerHTML = "";

    const wrapper = document.createElement("div");
    wrapper.className = "memory-panel";

    const intro = document.createElement("div");
    intro.className = "memory-section";
    const introTitle = document.createElement("div");
    introTitle.className = "memory-section-title";
    introTitle.textContent = "Read-only memory";
    const introText = document.createElement("div");
    introText.className = "memory-why";
    introText.textContent = "Memory events appear after a run. Edits are disabled in Studio.";
    intro.appendChild(introTitle);
    intro.appendChild(introText);
    wrapper.appendChild(intro);

    const entries = collectMemoryEntries(tracesList);
    if (!entries.length) {
      const hasRun = state && typeof state.getLastAction === "function" && state.getLastAction();
      const message = hasRun ? "No memory events for this action." : "No memory events yet. Run your app.";
      wrapper.appendChild(dom.buildEmpty(message));
      panel.appendChild(wrapper);
      return;
    }

    const section = document.createElement("div");
    section.className = "memory-section";
    const sectionTitle = document.createElement("div");
    sectionTitle.className = "memory-section-title";
    sectionTitle.textContent = "Recent memory";
    const list = document.createElement("div");
    list.className = "list memory-list";

    entries.forEach((entry) => {
      const item = document.createElement("div");
      item.className = "list-item";
      const line = document.createElement("div");
      line.className = "memory-line";
      const kind = document.createElement("div");
      kind.className = "memory-kind";
      kind.textContent = entry.kind.replace(/_/g, " ");
      const text = document.createElement("div");
      text.className = "memory-text";
      text.textContent = entry.text;
      line.appendChild(kind);
      line.appendChild(text);
      item.appendChild(line);
      list.appendChild(item);
    });

    section.appendChild(sectionTitle);
    section.appendChild(list);
    wrapper.appendChild(section);
    panel.appendChild(wrapper);
  }

  memory.renderMemory = renderMemory;
  window.renderMemory = renderMemory;
})();
