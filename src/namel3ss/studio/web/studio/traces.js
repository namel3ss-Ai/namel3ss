(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const dom = root.dom;
  const traces = root.traces || (root.traces = {});

  let filterText = "";
  let filterTimer = null;

  function formatTraceValue(value) {
    if (value === null || value === undefined || value === "") return "";
    if (typeof value === "string") return value;
    if (typeof formatPlainTrace === "function") return formatPlainTrace(value);
    try {
      return JSON.stringify(value, null, 2);
    } catch (err) {
      return String(value);
    }
  }

  function matchTrace(trace, needle) {
    if (!needle) return true;
    const values = [
      trace.type,
      trace.title,
      trace.provider,
      trace.model,
      trace.ai_name,
      trace.ai_profile_name,
      trace.agent_name,
      trace.input,
      trace.output,
      trace.result,
      trace.error,
    ]
      .map((v) => (typeof v === "string" ? v : v ? JSON.stringify(v) : ""))
      .join(" ")
      .toLowerCase();
    return values.includes(needle);
  }

  function appendDetail(container, label, value) {
    const block = document.createElement("div");
    block.className = "trace-detail";
    const heading = document.createElement("div");
    heading.className = "inline-label";
    heading.textContent = label;
    const body = document.createElement("div");
    const formatted = formatTraceValue(value);
    if (!formatted) {
      body.className = "trace-detail-empty";
      body.textContent = "No data.";
    } else {
      body.className = "trace-detail-value";
      body.textContent = formatted;
    }
    block.appendChild(heading);
    block.appendChild(body);
    container.appendChild(block);
  }

  function renderTraces(nextTraces) {
    const list = Array.isArray(nextTraces) ? nextTraces : state.getCachedTraces();
    const cached = state.setCachedTraces(list || []);
    const container = document.getElementById("traces");
    if (!container) return;
    container.innerHTML = "";

    const needle = filterText.trim().toLowerCase();
    const filtered = cached.filter((trace) => matchTrace(trace || {}, needle));
    if (!filtered.length) {
      const message = cached.length ? "No traces match filter." : "No traces yet. Run your app.";
      dom.showEmpty(container, message);
      if (window.renderMemory) window.renderMemory(cached);
      return;
    }

    const listNode = document.createElement("div");
    listNode.className = "list";

    filtered
      .slice()
      .reverse()
      .forEach((trace, idx) => {
        const row = document.createElement("div");
        row.className = "trace-row";
        if (trace && trace.error) row.classList.add("trace-error");

        const header = document.createElement("div");
        header.className = "trace-header";

        const summary = document.createElement("div");
        summary.className = "trace-summary";
        const summaryText = trace.title || trace.type || `Trace #${filtered.length - idx}`;
        summary.textContent = summaryText;

        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "trace-toggle";
        toggle.textContent = "Details";

        header.onclick = () => {
          row.classList.toggle("open");
          toggle.textContent = row.classList.contains("open") ? "Hide" : "Details";
        };

        header.appendChild(summary);
        header.appendChild(toggle);

        const details = document.createElement("div");
        details.className = "trace-details";

        appendDetail(details, "Input", trace.input);
        appendDetail(details, "Output", trace.output ?? trace.result);
        appendDetail(details, "Error", trace.error);
        appendDetail(details, "Tool calls", trace.tool_calls);
        appendDetail(details, "Tool results", trace.tool_results);

        row.appendChild(header);
        row.appendChild(details);
        listNode.appendChild(row);
      });

    container.appendChild(listNode);
    if (window.renderMemory) window.renderMemory(cached);
  }

  function setupFilter() {
    const input = document.getElementById("tracesFilter");
    if (!input) return;
    input.addEventListener("input", () => {
      if (filterTimer) window.clearTimeout(filterTimer);
      filterTimer = window.setTimeout(() => {
        filterText = input.value || "";
        renderTraces();
      }, 120);
    });
  }

  traces.renderTraces = renderTraces;
  traces.setupFilter = setupFilter;
  window.renderTraces = renderTraces;
})();
