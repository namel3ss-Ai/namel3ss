(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const dom = root.dom;
  const errors = root.errors || (root.errors = {});
  const secrets = root.secrets || {};
  const guidance = root.guidance || {};

  const PROVIDER_LABELS = {
    openai: "OpenAI",
    anthropic: "Anthropic",
    gemini: "Gemini",
    mistral: "Mistral",
  };
  const AI_CONTEXT_TITLE = "AI may not have the data it needs";
  const AI_CONTEXT_WHY = [
    "You queried app data in this flow, but the Ask AI input doesn't reference it.",
    "AI will answer generically unless you pass a context summary.",
  ];
  const AI_CONTEXT_FIX = [
    "Build a short context string from query results (cap it).",
    "Append the user question.",
    "Send the combined prompt to Ask AI.",
  ];

  function formatProvider(provider) {
    const key = String(provider || "").trim().toLowerCase();
    return PROVIDER_LABELS[key] || (key ? key.toUpperCase() : "Provider");
  }

  function normalizeCategory(category) {
    const value = String(category || "").trim();
    return value || "unknown";
  }

  function redactText(text) {
    return String(text || "")
      .replace(/Bearer\\s+[A-Za-z0-9._-]+/gi, "Bearer [redacted]")
      .replace(/sk-[A-Za-z0-9_-]+/g, "[redacted]");
  }

  function normalizeLineBreaks(text) {
    if (typeof text !== "string") return text;
    if (!text.includes("\\n")) return text;
    return text.replaceAll("\\n", "\n");
  }

  function expandPlaceholders(provider, text) {
    if (typeof secrets.expandPlaceholders === "function") {
      return secrets.expandPlaceholders(provider, text);
    }
    return text;
  }

  function sanitizeDiagnostic(value) {
    if (value === null || value === undefined) return value;
    if (typeof value === "string") return redactText(value);
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

  function getLastRunError() {
    if (!state || typeof state.getCachedLastRunError !== "function") return null;
    return state.getCachedLastRunError();
  }

  function extractErrorText(payload) {
    if (!payload) return "";
    if (typeof payload === "string") return payload;
    if (payload.error) return payload.error;
    if (payload.message) return payload.message;
    return "";
  }

  function parseGuidanceSections(text) {
    const parsed = guidance.parseGuidance ? guidance.parseGuidance(text) : { raw: text };
    return {
      what: redactText(parsed.what || parsed.raw || ""),
      why: redactText(parsed.why || ""),
      fix: redactText(parsed.fix || ""),
      where: redactText(parsed.where || ""),
      example: redactText(parsed.example || ""),
      raw: redactText(parsed.raw || ""),
    };
  }

  function shouldShowSetupForError(text) {
    const value = String(text || "");
    if (/NAMEL3SS_[A-Z0-9_]+/.test(value)) return true;
    if (/_API_KEY/.test(value)) return true;
    return /secret|api key/i.test(value);
  }

  function resolveErrorLocation(payload, parsedWhere) {
    if (parsedWhere) return parsedWhere;
    const location = payload && payload.location ? payload.location : null;
    const file = payload && payload.details ? payload.details.file : null;
    if (!location || (!location.line && !location.column) && !file) return "";
    const parts = [];
    if (file) parts.push(`File: ${file}`);
    if (location && location.line) {
      const col = location.column ? `, column ${location.column}` : "";
      parts.push(`line ${location.line}${col}`);
    }
    return parts.join(" ");
  }

  function getStaticAiContextDiagnostics() {
    if (!state || typeof state.getCachedDiagnostics !== "function") return [];
    const payload = state.getCachedDiagnostics();
    const list = payload && Array.isArray(payload.diagnostics) ? payload.diagnostics : [];
    return list.filter((item) => item && String(item.id || "").startsWith("AI_CONTEXT_"));
  }

  function textLooksQuestionLike(text) {
    if (!text) return false;
    const trimmed = String(text).trim().toLowerCase();
    if (!trimmed) return false;
    if (trimmed.includes("?")) return true;
    const starters = ["which", "what", "why", "how", "lowest", "highest", "top", "most", "least"];
    return starters.some((word) => trimmed.startsWith(`${word} `) || trimmed.includes(` ${word} `));
  }

  function hasContextMarkers(text) {
    if (!text) return false;
    const lower = String(text).toLowerCase();
    const emptyMarkers = [
      "(none found)",
      "no records found",
      "no orders found",
      "no data found",
      "0 records",
      "0 orders",
    ];
    if (emptyMarkers.some((marker) => lower.includes(marker))) return true;
    if (lower.includes("records:") || lower.includes("record:") || lower.includes("data:")) return true;
    if (/\bn\s*=\s*\d+/.test(lower)) return true;
    const lines = String(text)
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    const listLines = lines.filter((line) => line.startsWith("- ") || line.startsWith("* "));
    return listLines.length >= 2;
  }

  function hasDataUsage(traces) {
    const list = Array.isArray(traces) ? traces : [];
    return list.some((trace) => {
      if (!trace || typeof trace !== "object") return false;
      if (["tool_call", "tool_call_requested", "tool_call_completed", "tool_call_failed"].includes(trace.type)) {
        return true;
      }
      if ((trace.tool_calls && trace.tool_calls.length) || (trace.tool_results && trace.tool_results.length)) {
        return true;
      }
      if (trace.record || trace.record_name) return true;
      const events = Array.isArray(trace.canonical_events) ? trace.canonical_events : [];
      return events.some((event) => {
        const type = event && event.type ? String(event.type) : "";
        return type.startsWith("tool_call");
      });
    });
  }

  function collectRuntimeAiContextDiagnostics(traces) {
    const list = Array.isArray(traces) ? traces : [];
    if (!list.length || !hasDataUsage(list)) return [];
    let latest = null;
    list.forEach((trace) => {
      if (!trace || typeof trace !== "object") return;
      if (!trace.ai_name && !trace.ai_profile_name) return;
      const input = trace.input;
      if (typeof input !== "string" || input.length > 400) return;
      if (!textLooksQuestionLike(input)) return;
      if (hasContextMarkers(input)) return;
      latest = trace;
    });
    if (!latest) return [];
    return [
      {
        id: "AI_CONTEXT_LIKELY_MISSING",
        category: "AI Design Warning",
        severity: "warning",
        message: "This AI call looks like a data question, but the AI input is mostly the question text.",
        hint: "Include a compact summary of relevant records/tool output in the AI prompt.",
        source: "runtime",
      },
    ];
  }

  function getLatestProviderError(traces) {
    const list = Array.isArray(traces) ? traces : [];
    let latest = null;
    list.forEach((trace) => {
      const events = trace && Array.isArray(trace.canonical_events) ? trace.canonical_events : [];
      events.forEach((event) => {
        if (event && event.type === "ai_provider_error") {
          latest = event;
        }
      });
    });
    return latest;
  }

  function buildFixSteps(diagnostic) {
    const category = normalizeCategory(diagnostic && diagnostic.category);
    const provider = String((diagnostic && diagnostic.provider) || "").toLowerCase();
    const envLine = "Set <CANONICAL_KEY> (preferred) or <ALIAS_KEY>.";
    const steps = {
      missing_key: [
        "cp .env.example .env",
        envLine,
        "n3 secrets status --json",
      ],
      auth: [
        "Check your API key and permissions",
        envLine,
        "n3 secrets status --json",
      ],
      model_access: [
        "Use a model you have access to",
        "Update the model name in app.ai",
        "Retry the action",
      ],
      rate_limit: [
        "Wait a moment and retry",
        "Reduce concurrent requests if needed",
      ],
      quota: [
        "Check provider billing or quota",
        "Retry after quota is available",
      ],
      network: [
        "Check network connectivity",
        "Retry the action",
      ],
      server: [
        "Provider is unavailable",
        "Retry shortly",
      ],
      malformed_request: [
        "Check model name and inputs",
        "Retry the action",
      ],
      timeout: [
        "Retry the action",
        "Check your network or VPN",
      ],
      unknown: [
        "Review diagnostics in Traces",
        "Retry the action",
      ],
    };
    const lines = steps[category] || steps.unknown;
    const joined = lines.map((line) => expandPlaceholders(provider, line)).join("\n");
    return normalizeLineBreaks(joined);
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

  function shouldShowSetup(diagnostic) {
    const category = normalizeCategory(diagnostic && diagnostic.category);
    if (category === "missing_key" || category === "auth") return true;
    if (root.setup && typeof root.setup.getMissingSecrets === "function") {
      const missing = root.setup.getMissingSecrets();
      if (Array.isArray(missing) && missing.length) return true;
    }
    return false;
  }

  function openTab(name) {
    if (root.dock && typeof root.dock.setActiveTab === "function") {
      root.dock.setActiveTab(name);
    }
  }

  function updateErrorBanner(diagnostic) {
    const banner = document.getElementById("errorBanner");
    if (!banner) return;
    const runError = getLastRunError();
    if (runError) {
      banner.textContent = "Run failed. Click for details.";
      banner.classList.remove("hidden");
      banner.onclick = () => openTab("errors");
      return;
    }
    if (!diagnostic) {
      banner.classList.add("hidden");
      banner.textContent = "";
      banner.onclick = null;
      return;
    }
    const provider = formatProvider(diagnostic.provider);
    const category = normalizeCategory(diagnostic.category);
    banner.textContent = `${provider} failed (${category}). Click for details.`;
    banner.classList.remove("hidden");
    banner.onclick = () => openTab("errors");
  }

  function buildFieldRow(label, value) {
    const row = document.createElement("div");
    row.className = "error-field";
    const title = document.createElement("div");
    title.className = "error-field-label";
    title.textContent = label;
    const text = document.createElement("div");
    text.className = "error-field-value";
    text.textContent = value ? String(value) : "-";
    row.appendChild(title);
    row.appendChild(text);
    return row;
  }

  function buildDetailRow(label, value) {
    const row = document.createElement("div");
    row.className = "error-detail";
    const title = document.createElement("div");
    title.className = "error-detail-label";
    title.textContent = label;
    const text = document.createElement("div");
    text.className = "error-detail-value";
    text.textContent = value ? String(value) : "-";
    row.appendChild(title);
    row.appendChild(text);
    return row;
  }

  function buildProviderErrorCard(diagnostic) {
    const card = document.createElement("div");
    card.className = "error-card";

    const header = document.createElement("div");
    header.className = "error-card-header";
    const title = document.createElement("div");
    title.className = "error-card-title";
    title.textContent = `${formatProvider(diagnostic.provider)} failed`;
    const badge = document.createElement("span");
    badge.className = "error-badge";
    badge.textContent = normalizeCategory(diagnostic.category);
    header.appendChild(title);
    header.appendChild(badge);

    const hint = document.createElement("div");
    hint.className = "error-hint";
    const rawHint = diagnostic.hint || "Check the diagnostics and try again.";
    hint.textContent = normalizeLineBreaks(expandPlaceholders(diagnostic.provider, rawHint));

    const fields = document.createElement("div");
    fields.className = "error-fields";
    fields.appendChild(buildFieldRow("URL", diagnostic.url));
    fields.appendChild(buildFieldRow("Status", diagnostic.status));

    const stepsTitle = document.createElement("div");
    stepsTitle.className = "panel-section-title";
    stepsTitle.textContent = "Fix steps";
    const steps = document.createElement("div");
    steps.className = "code-block fix-steps";
    steps.textContent = normalizeLineBreaks(buildFixSteps(diagnostic));

    const actions = document.createElement("div");
    actions.className = "json-actions";
    const copyDiagnostics = document.createElement("button");
    copyDiagnostics.type = "button";
    copyDiagnostics.className = "btn ghost";
    copyDiagnostics.textContent = "Copy diagnostics JSON";
    copyDiagnostics.onclick = () => {
      copyText(diagnostic);
    };
    const copyFix = document.createElement("button");
    copyFix.type = "button";
    copyFix.className = "btn ghost";
    copyFix.textContent = "Copy fix steps";
    copyFix.onclick = () => {
      copyText(buildFixSteps(diagnostic));
    };
    actions.appendChild(copyDiagnostics);
    actions.appendChild(copyFix);

    if (shouldShowSetup(diagnostic)) {
      const openSetup = document.createElement("button");
      openSetup.type = "button";
      openSetup.className = "btn ghost";
      openSetup.textContent = "Open Setup";
      openSetup.onclick = () => openTab("setup");
      actions.appendChild(openSetup);
    }

    const openTraces = document.createElement("button");
    openTraces.type = "button";
    openTraces.className = "btn ghost";
    openTraces.textContent = "Open Traces";
    openTraces.onclick = () => openTab("traces");
    actions.appendChild(openTraces);

    card.appendChild(header);
    card.appendChild(hint);
    card.appendChild(fields);
    card.appendChild(stepsTitle);
    card.appendChild(steps);
    card.appendChild(actions);
    return card;
  }

  function buildAiContextCard(diagnostic) {
    const card = document.createElement("div");
    card.className = "error-card";

    const header = document.createElement("div");
    header.className = "error-card-header";
    const title = document.createElement("div");
    title.className = "error-card-title";
    title.textContent = AI_CONTEXT_TITLE;
    const badge = document.createElement("span");
    badge.className = "error-badge";
    badge.textContent = diagnostic.category || "AI Design Warning";
    header.appendChild(title);
    header.appendChild(badge);

    const summary = document.createElement("div");
    summary.className = "error-hint";
    summary.textContent = diagnostic.message || "AI input may be missing app data context.";

    const hint = document.createElement("div");
    hint.className = "error-hint";
    hint.textContent = diagnostic.hint || "Include a compact summary of relevant records or tool output.";

    const whyTitle = document.createElement("div");
    whyTitle.className = "panel-section-title";
    whyTitle.textContent = "Why";
    const whyList = document.createElement("ul");
    whyList.className = "error-why";
    AI_CONTEXT_WHY.forEach((line) => {
      const item = document.createElement("li");
      item.textContent = line;
      whyList.appendChild(item);
    });

    const fields = document.createElement("div");
    fields.className = "error-fields";
    if (diagnostic.flow) {
      fields.appendChild(buildFieldRow("Flow", diagnostic.flow));
      if (diagnostic.line) {
        const location = diagnostic.column ? `${diagnostic.line}:${diagnostic.column}` : String(diagnostic.line);
        fields.appendChild(buildFieldRow("Location", location));
      }
    }

    const stepsTitle = document.createElement("div");
    stepsTitle.className = "panel-section-title";
    stepsTitle.textContent = "How to fix";
    const steps = document.createElement("div");
    steps.className = "code-block fix-steps";
    steps.textContent = AI_CONTEXT_FIX.join("\n");

    const actions = document.createElement("div");
    actions.className = "json-actions";
    const copyFix = document.createElement("button");
    copyFix.type = "button";
    copyFix.className = "btn ghost";
    copyFix.textContent = "Copy fix snippet";
    copyFix.onclick = () => {
      copyText(AI_CONTEXT_FIX.join("\n"));
    };
    actions.appendChild(copyFix);

    if (diagnostic.flow) {
      const viewFlow = document.createElement("button");
      viewFlow.type = "button";
      viewFlow.className = "btn ghost";
      viewFlow.textContent = "View flow";
      viewFlow.onclick = () => openTab("graph");
      actions.appendChild(viewFlow);
    }

    card.appendChild(header);
    card.appendChild(summary);
    card.appendChild(hint);
    card.appendChild(whyTitle);
    card.appendChild(whyList);
    if (fields.childNodes.length) {
      card.appendChild(fields);
    }
    card.appendChild(stepsTitle);
    card.appendChild(steps);
    card.appendChild(actions);
    return card;
  }

  function buildRunErrorCard(payload) {
    const card = document.createElement("div");
    card.className = "error-card";
    const rawText = extractErrorText(payload);
    const parsed = parseGuidanceSections(rawText);
    const where = resolveErrorLocation(payload, parsed.where);

    const header = document.createElement("div");
    header.className = "error-card-header";
    const title = document.createElement("div");
    title.className = "error-card-title";
    title.textContent = "Last run error";
    const badge = document.createElement("span");
    badge.className = "error-badge";
    badge.textContent = "run error";
    header.appendChild(title);
    header.appendChild(badge);

    const detailStack = document.createElement("div");
    detailStack.className = "error-details";
    if (parsed.what) {
      detailStack.appendChild(buildDetailRow("What happened", parsed.what));
    } else if (parsed.raw) {
      detailStack.appendChild(buildDetailRow("What happened", parsed.raw));
    }
    if (where) {
      detailStack.appendChild(buildDetailRow("Where", where));
    }
    if (parsed.why) {
      detailStack.appendChild(buildDetailRow("Why", parsed.why));
    }

    const fixText = [parsed.fix, parsed.example].filter(Boolean).join("\n");
    const stepsTitle = document.createElement("div");
    stepsTitle.className = "panel-section-title";
    stepsTitle.textContent = "How to fix";
    const steps = document.createElement("div");
    steps.className = "code-block fix-steps";
    steps.textContent = normalizeLineBreaks(fixText);

    const actions = document.createElement("div");
    actions.className = "json-actions";
    const copyError = document.createElement("button");
    copyError.type = "button";
    copyError.className = "btn ghost";
    copyError.textContent = "Copy error JSON";
    copyError.onclick = () => copyText(payload);
    actions.appendChild(copyError);

    if (fixText) {
      const copyFix = document.createElement("button");
      copyFix.type = "button";
      copyFix.className = "btn ghost";
      copyFix.textContent = "Copy fix steps";
      copyFix.onclick = () => copyText(fixText);
      actions.appendChild(copyFix);
    }

    if (shouldShowSetupForError(parsed.raw || parsed.fix || parsed.what)) {
      const openSetup = document.createElement("button");
      openSetup.type = "button";
      openSetup.className = "btn ghost";
      openSetup.textContent = "Open Setup";
      openSetup.onclick = () => openTab("setup");
      actions.appendChild(openSetup);
    }

    if (where) {
      const openGraph = document.createElement("button");
      openGraph.type = "button";
      openGraph.className = "btn ghost";
      openGraph.textContent = "Open Graph";
      openGraph.onclick = () => openTab("graph");
      actions.appendChild(openGraph);
    }

    const openTraces = document.createElement("button");
    openTraces.type = "button";
    openTraces.className = "btn ghost";
    openTraces.textContent = "Open Traces";
    openTraces.onclick = () => openTab("traces");
    actions.appendChild(openTraces);

    card.appendChild(header);
    card.appendChild(detailStack);
    if (fixText) {
      card.appendChild(stepsTitle);
      card.appendChild(steps);
    }
    card.appendChild(actions);
    return card;
  }

  function renderErrors(nextTraces) {
    const panel = document.getElementById("errors");
    if (!panel) return;
    const traces = Array.isArray(nextTraces) ? nextTraces : (state && state.getCachedTraces ? state.getCachedTraces() : []);
    const runError = getLastRunError();
    const event = getLatestProviderError(traces);
    const providerDiagnostic = event && event.diagnostic ? sanitizeDiagnostic(event.diagnostic || {}) : null;
    const safeRunError = runError ? sanitizeDiagnostic(runError) : null;
    const staticDiagnostics = getStaticAiContextDiagnostics().map((item) => sanitizeDiagnostic(item));
    const runtimeDiagnostics = collectRuntimeAiContextDiagnostics(traces).map((item) => sanitizeDiagnostic(item));
    const seen = new Set();
    const aiDiagnostics = [...staticDiagnostics, ...runtimeDiagnostics].filter((item) => {
      if (!item) return false;
      const key = `${item.id || ""}|${item.flow || ""}|${item.source || ""}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    if (!providerDiagnostic && !aiDiagnostics.length && !safeRunError) {
      updateErrorBanner(null);
      dom.showEmpty(panel, "No provider errors yet.");
      return;
    }

    updateErrorBanner(providerDiagnostic);
    panel.innerHTML = "";
    const stack = document.createElement("div");
    stack.className = "panel-stack";
    if (safeRunError) {
      stack.appendChild(buildRunErrorCard(safeRunError));
    }
    if (providerDiagnostic) {
      stack.appendChild(buildProviderErrorCard(providerDiagnostic));
    }
    aiDiagnostics.forEach((diagnostic) => {
      stack.appendChild(buildAiContextCard(diagnostic));
    });
    panel.appendChild(stack);
  }

  errors.renderErrors = renderErrors;
  errors.updateErrorBanner = updateErrorBanner;
  window.renderErrors = renderErrors;
})();
