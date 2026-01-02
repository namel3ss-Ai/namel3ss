(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const dom = root.dom;
  const traces = root.traces || (root.traces = {});
  const secrets = root.secrets || {};

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

  function redactTraceText(text) {
    return String(text || "")
      .replace(/Bearer\\s+[A-Za-z0-9._-]+/gi, "Bearer [redacted]")
      .replace(/sk-[A-Za-z0-9_-]+/g, "[redacted]");
  }

  function sanitizeDiagnostic(value) {
    if (value === null || value === undefined) return value;
    if (typeof value === "string") return redactTraceText(value);
    if (Array.isArray(value)) return value.map((item) => sanitizeDiagnostic(item));
    if (typeof value === "object") {
      const result = {};
      Object.keys(value).forEach((key) => {
        result[key] = sanitizeDiagnostic(value[key]);
      });
      return result;
    }
    return value;
  }

  function expandPlaceholders(provider, text) {
    if (typeof secrets.expandPlaceholders === "function") {
      return secrets.expandPlaceholders(provider, text);
    }
    return text;
  }

  function copyText(text) {
    const value = typeof text === "string" ? text : JSON.stringify(text, null, 2);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(value);
      return;
    }
    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.setAttribute("readonly", "true");
    textarea.style.position = "absolute";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }

  function providerErrors(trace) {
    const events = trace && Array.isArray(trace.canonical_events) ? trace.canonical_events : [];
    return events.filter((event) => event && event.type === "ai_provider_error");
  }

  function latestProviderError(trace) {
    const errors = providerErrors(trace);
    if (!errors.length) return null;
    return errors[errors.length - 1];
  }

  function buildFixSteps(diagnostic) {
    const parts = [];
    const provider = diagnostic && diagnostic.provider ? String(diagnostic.provider).toLowerCase() : "";
    const hint = diagnostic && diagnostic.hint ? String(diagnostic.hint) : "";
    if (hint) parts.push(expandPlaceholders(provider, hint));
    parts.push(expandPlaceholders(provider, "Set <CANONICAL_KEY> (preferred) or <ALIAS_KEY>."));
    return parts.filter(Boolean).join("\\n").trim();
  }

  function buildDiagnosticActions(diagnostic) {
    const row = document.createElement("div");
    row.className = "json-actions";
    const safeDiagnostic = sanitizeDiagnostic(diagnostic || {});
    const copyDiagnostic = document.createElement("button");
    copyDiagnostic.type = "button";
    copyDiagnostic.className = "btn ghost";
    copyDiagnostic.textContent = "Copy diagnostics JSON";
    copyDiagnostic.onclick = () => copyText(JSON.stringify(safeDiagnostic, null, 2));
    const copyFix = document.createElement("button");
    copyFix.type = "button";
    copyFix.className = "btn ghost";
    copyFix.textContent = "Copy fix steps";
    copyFix.onclick = () => copyText(buildFixSteps(safeDiagnostic));
    row.appendChild(copyDiagnostic);
    row.appendChild(copyFix);
    return row;
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

  function appendProviderDiagnostics(container, trace) {
    const error = latestProviderError(trace);
    if (!error || !error.diagnostic) return;
    const diagnostic = sanitizeDiagnostic(error.diagnostic || {});
    appendDetail(container, "Provider", diagnostic.provider);
    appendDetail(container, "Category", diagnostic.category);
    appendDetail(container, "Hint", diagnostic.hint);
    appendDetail(container, "Status", diagnostic.status);
    appendDetail(container, "Code", diagnostic.code);
    appendDetail(container, "Type", diagnostic.type);
    appendDetail(container, "URL", diagnostic.url);
    appendDetail(container, "Message", diagnostic.message);
    container.appendChild(buildDiagnosticActions(diagnostic));
  }

  function renderTraces(nextTraces) {
    const list = Array.isArray(nextTraces) ? nextTraces : state.getCachedTraces();
    const cached = state.setCachedTraces(list || []);
    if (root.errors && typeof root.errors.renderErrors === "function") {
      root.errors.renderErrors(cached);
    }
    const container = document.getElementById("traces");
    if (!container) return;
    container.innerHTML = "";

    const needle = filterText.trim().toLowerCase();
    const filtered = cached.filter((trace) => matchTrace(trace || {}, needle));
    if (!filtered.length) {
      const hasRun = state && typeof state.getLastAction === "function" && state.getLastAction();
      const message = cached.length
        ? "No traces match filter."
        : hasRun
          ? "This action emitted no traces."
          : "No traces yet. Run your app.";
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
        appendProviderDiagnostics(details, trace);

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
