(() => {
  const root = window.N3App || (window.N3App = {});
  const traces = root.traces || (root.traces = {});
  const utils = root.utils;
  const state = root.state;

  let agreementsRenderer = null;

  function setAgreementsRenderer(fn) {
    agreementsRenderer = fn;
  }

  function matchTrace(trace, needle) {
    if (!needle) return true;
    const eventTypes = (trace.canonical_events || []).map((event) => event.type).join(" ");
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
      trace.lines,
      eventTypes,
    ]
      .map((v) => (typeof v === "string" ? v : v ? JSON.stringify(v) : ""))
      .join(" ")
      .toLowerCase();
    return values.includes(needle);
  }

  function isModuleTrace(trace) {
    const type = trace && typeof trace.type === "string" ? trace.type : "";
    return type === "module_loaded" || type === "module_merged" || type === "module_overrides";
  }

  function isParallelTrace(trace) {
    const type = trace && typeof trace.type === "string" ? trace.type : "";
    return type === "parallel_started" || type === "parallel_task_finished" || type === "parallel_merged";
  }

  function renderTraces(data) {
    const cachedTraces = state.setCachedTraces(Array.isArray(data) ? data : state.getCachedTraces());
    state.setSelectedTrace(null);
    const container = document.getElementById("traces");
    if (!container) return;
    container.innerHTML = "";
    const filtered = cachedTraces
      .filter((t) => matchTrace(t, state.getTraceFilterText()))
      .filter((t) => {
        if (isModuleTrace(t)) {
          const filters = state.getModuleTraceFilters() || {};
          return filters[t.type] !== false;
        }
        if (isParallelTrace(t)) {
          const filters = state.getParallelTraceFilters() || {};
          return filters[t.type] !== false;
        }
        return true;
      });
    const traceItems = filtered.slice().reverse();
    if (!traceItems.length) {
      const message = cachedTraces.length
        ? "No traces match filter."
        : "No traces yet \u2014 run a flow to generate traces.";
      utils.showEmpty(container, message);
      utils.updateCopyButton("tracesCopy", () => "[]");
      if (window.updateTraceCopyButtons) window.updateTraceCopyButtons();
      return;
    }
    const list = document.createElement("div");
    list.className = "list";
    traceItems.forEach((trace, idx) => {
      const row = document.createElement("div");
      row.className = "trace-row";
      const header = document.createElement("div");
      header.className = "trace-header";
      const title = document.createElement("div");
      title.className = "trace-title";
      title.textContent = `Trace #${traceItems.length - idx}`;
      const meta = document.createElement("div");
      meta.className = "trace-meta";
      const model = trace.model ? `model: ${trace.model}` : undefined;
      const aiName = trace.ai_name ? `ai: ${trace.ai_name}` : undefined;
      const status = trace.error ? "status: error" : "status: ok";
      meta.textContent = [model, aiName, status].filter(Boolean).join(" \u00b7 ");
      header.appendChild(title);
      header.appendChild(meta);
      const details = document.createElement("div");
      details.className = "trace-details";
      if (isModuleTrace(trace)) {
        const label = trace.title || "Module event";
        traces.appendTraceSection(details, label, trace.lines || trace, false, state.getTraceRenderMode());
      } else if (isParallelTrace(trace)) {
        const label = trace.title || "Parallel";
        traces.appendTraceSection(details, label, trace.lines || trace, false, state.getTraceRenderMode());
      } else if (trace.type === "parallel_agents" && Array.isArray(trace.agents)) {
        traces.appendTraceSection(details, "Agents", trace.agents, false, state.getTraceRenderMode());
      } else {
        traces.appendTraceSection(details, "Input", trace.input, false, state.getTraceRenderMode());
        traces.appendTraceSection(details, "Memory", trace.memory, false, state.getTraceRenderMode());
        const phaseId = traces.currentPhaseIdForTrace(trace);
        if (traces.appendWakeUpSection) {
          traces.appendWakeUpSection(details, trace);
        }
        if (traces.appendMemoryPackSection) {
          traces.appendMemoryPackSection(details, trace);
        }
        traces.appendMemoryBudgetSection(details, trace, phaseId);
        traces.appendMemoryEventsSection(details, trace, phaseId, state.getTraceRenderMode());
        traces.appendTraceSection(details, "Tool calls", trace.tool_calls, false, state.getTraceRenderMode());
        traces.appendTraceSection(details, "Tool results", trace.tool_results, false, state.getTraceRenderMode());
        traces.appendTraceSection(details, "Output", trace.output ?? trace.result, true, state.getTraceRenderMode());
      }
      row.appendChild(header);
      row.appendChild(details);
      header.onclick = () => {
        row.classList.toggle("open");
        state.setSelectedTrace(trace);
        if (window.updateTraceCopyButtons) window.updateTraceCopyButtons();
      };
      list.appendChild(row);
    });
    container.appendChild(list);
    utils.updateCopyButton("tracesCopy", () => JSON.stringify(cachedTraces || [], null, 2));
    if (window.updateTraceCopyButtons) window.updateTraceCopyButtons();
    if (agreementsRenderer) {
      agreementsRenderer(state.getCachedAgreements());
    }
  }

  traces.matchTrace = matchTrace;
  traces.renderTraces = renderTraces;
  traces.setAgreementsRenderer = setAgreementsRenderer;
  window.renderTraces = renderTraces;
})();
