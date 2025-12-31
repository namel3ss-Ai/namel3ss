(() => {
  const root = window.N3App || (window.N3App = {});
  const render = root.render || (root.render = {});
  const utils = root.utils;
  const state = root.state;

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

  function formatList(items) {
    if (!items.length) return "none";
    const sorted = Array.from(items).filter(Boolean).sort();
    if (sorted.length <= 3) return sorted.join(", ");
    return `${sorted.slice(0, 3).join(", ")} and ${sorted.length - 3} more`;
  }

  function summarizeWhy(tracesList) {
    if (!Array.isArray(tracesList) || tracesList.length === 0) return null;
    const aiNames = new Set();
    const toolNames = new Set();
    const errorReasons = [];
    let memoryRecallCount = 0;
    let memoryWriteCount = 0;
    let memoryRecallQuery = "";

    function noteError(reason) {
      const cleaned = normalizeText(reason, 140).replace(/[.]+$/, "");
      if (cleaned) errorReasons.push(cleaned);
    }

    function visitTrace(trace) {
      if (!trace || typeof trace !== "object") return;
      if (trace.type === "parallel_agents" && Array.isArray(trace.agents)) {
        trace.agents.forEach((agentTrace) => visitTrace(agentTrace));
        return;
      }
      const aiName = trace.ai_name || trace.ai_profile_name || "";
      if (Array.isArray(trace.canonical_events)) {
        trace.canonical_events.forEach((event) => {
          if (!event || typeof event.type !== "string") return;
          if (event.type === "ai_call_started" || event.type === "ai_call_completed" || event.type === "ai_call_failed") {
            if (aiName) aiNames.add(aiName);
            if (event.type === "ai_call_failed") {
              noteError(event.error_message || "AI call failed.");
            }
          }
          if (event.type === "tool_call_requested" || event.type === "tool_call_completed" || event.type === "tool_call_failed") {
            if (event.tool_name) toolNames.add(event.tool_name);
            if (event.type === "tool_call_failed") {
              const toolLabel = event.tool_name ? `${event.tool_name} failed.` : "Tool call failed.";
              noteError(event.error_message ? `${toolLabel} ${event.error_message}` : toolLabel);
            }
          }
          if (event.type === "memory_recall") {
            memoryRecallCount += Array.isArray(event.recalled) ? event.recalled.length : 0;
            if (!memoryRecallQuery) {
              memoryRecallQuery = normalizeText(event.query, 120);
            }
          }
          if (event.type === "memory_write") {
            memoryWriteCount += Array.isArray(event.written) ? event.written.length : 0;
          }
        });
      }
      if (trace.type === "tool_call") {
        if (trace.tool_name || trace.tool) toolNames.add(trace.tool_name || trace.tool);
        if (trace.status === "error") {
          const toolLabel = trace.tool_name || trace.tool;
          const base = toolLabel ? `${toolLabel} failed.` : "Tool failed.";
          noteError(trace.error_message ? `${base} ${trace.error_message}` : base);
        }
      }
      if (trace.type === "runtime_error") {
        noteError("A runtime error occurred.");
      }
    }

    tracesList.forEach((trace) => visitTrace(trace));

    const happened = [];
    happened.push("Flow started.");
    if (aiNames.size) {
      happened.push(`AI called: ${formatList(aiNames)}.`);
    }
    if (toolNames.size) {
      happened.push(`Tool ran: ${formatList(toolNames)}.`);
    }
    if (memoryRecallCount) {
      happened.push(`Memory recalled: ${memoryRecallCount} item${memoryRecallCount === 1 ? "" : "s"}.`);
    }
    if (memoryWriteCount) {
      happened.push(`Memory written: ${memoryWriteCount} item${memoryWriteCount === 1 ? "" : "s"}.`);
    }
    if (errorReasons.length) {
      happened.push(`Couldn't complete because ${errorReasons[0]}.`);
    }
    happened.push(errorReasons.length ? "Flow ended with errors." : "Flow ended.");
    const fallback = [];
    if (!aiNames.size) fallback.push("No AI calls were recorded.");
    if (!toolNames.size) fallback.push("No tools ran.");
    if (!errorReasons.length) fallback.push("No errors were recorded.");
    while (happened.length < 3 && fallback.length) {
      happened.splice(happened.length - 1, 0, fallback.shift());
    }
    while (happened.length > 8) {
      const removeIndex = memoryWriteCount || memoryRecallCount ? happened.length - 2 : 1;
      happened.splice(removeIndex, 1);
    }

    const why = [];
    if (memoryRecallCount) {
      if (memoryRecallQuery) {
        why.push(`Because the request matched "${memoryRecallQuery}".`);
      } else {
        why.push("Because memory was recalled for context.");
      }
    }
    if (toolNames.size) {
      why.push(`Because the flow needed tools: ${formatList(toolNames)}.`);
    }
    if (memoryWriteCount) {
      why.push("Because the response introduced new information.");
    }
    if (errorReasons.length) {
      why.push(`Because an error interrupted the run: ${errorReasons[0]}.`);
    }
    if (!why.length) {
      why.push("Not recorded for this run.");
    }

    const didnt = [];
    if (!aiNames.size) didnt.push("No AI calls were recorded.");
    if (!toolNames.size) didnt.push("No tools ran.");
    if (!memoryRecallCount) didnt.push("No memory was recalled.");
    if (!memoryWriteCount) didnt.push("No memory was written.");
    if (!errorReasons.length) didnt.push("No errors were recorded.");
    if (!didnt.length) {
      didnt.push("Not recorded for this run.");
    }

    return { happened, why, didnt };
  }

  function renderList(items) {
    const list = document.createElement("ul");
    list.className = "why-list";
    items.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      list.appendChild(li);
    });
    return list;
  }

  function renderSection(title, items) {
    const section = document.createElement("div");
    section.className = "why-section";
    const heading = document.createElement("div");
    heading.className = "why-section-title";
    heading.textContent = title;
    section.appendChild(heading);
    section.appendChild(renderList(items));
    return section;
  }

  function renderWhyPanel(tracesList) {
    const panel = document.getElementById("why");
    if (!panel) return;
    panel.innerHTML = "";
    if (state.getLastRunStatus && state.getLastRunStatus() === "error") {
      utils.showError(panel, state.getLastRunError && state.getLastRunError());
      return;
    }
    const traces = Array.isArray(tracesList) ? tracesList : state.getCachedTraces();
    const summary = summarizeWhy(traces);
    if (!summary) {
      utils.showEmpty(panel, "Run your app to see why it behaved the way it did.");
      return;
    }
    const wrapper = document.createElement("div");
    wrapper.className = "why-panel";
    const title = document.createElement("div");
    title.className = "why-title";
    title.textContent = "Why this run behaved this way";
    wrapper.appendChild(title);
    wrapper.appendChild(renderSection("What happened", summary.happened));
    wrapper.appendChild(renderSection("Why", summary.why));
    wrapper.appendChild(renderSection("What didn't happen", summary.didnt));
    panel.appendChild(wrapper);
  }

  function refreshWhyPanel() {
    renderWhyPanel();
  }

  render.renderWhyPanel = renderWhyPanel;
  render.refreshWhyPanel = refreshWhyPanel;
  window.renderWhyPanel = renderWhyPanel;
  window.refreshWhyPanel = refreshWhyPanel;
})();
