(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const dom = root.dom;
  const explain = root.explain || (root.explain = {});

  function getContainer() {
    return document.getElementById("explain");
  }

  function formatValue(value) {
    if (value === null || value === undefined) return "null";
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    try {
      return JSON.stringify(value, null, 2);
    } catch (err) {
      return String(value);
    }
  }

  function formatSteps(value) {
    if (typeof window.formatPlainTrace === "function") {
      return window.formatPlainTrace(value);
    }
    return formatValue(value);
  }

  function extractExplainTraces(traces) {
    const data = Array.isArray(traces)
      ? traces
      : state && typeof state.getCachedTraces === "function"
        ? state.getCachedTraces()
        : [];
    return data.filter(
      (trace) =>
        trace &&
        (trace.type === "expression_explain" || trace.type === "answer_explain")
    );
  }

  function summarizeSpan(trace) {
    const span = trace && trace.span ? trace.span : {};
    const line = span.line_start || span.line || null;
    if (!line) return null;
    const flow = trace.flow ? `flow "${trace.flow}"` : "calc";
    return `${flow} · line ${line}`;
  }

  function jumpToFormula(trace) {
    const span = trace && trace.span ? trace.span : {};
    const line = span.line_start || span.line;
    if (!line || !root.dock || typeof root.dock.setActiveTab !== "function") return;
    root.dock.setActiveTab("formulas");
    window.setTimeout(() => {
      if (root.formulas && typeof root.formulas.highlightLine === "function") {
        root.formulas.highlightLine(line);
      }
    }, 0);
  }

  function renderExplain(traces) {
    const container = getContainer();
    if (!container) return;
    const items = extractExplainTraces(traces);
    if (!items.length) {
      dom.showEmpty(container, "No explanations yet.");
      return;
    }
    container.innerHTML = "";
    items
      .slice()
      .reverse()
      .forEach((trace) => {
        const card =
          trace.type === "answer_explain"
            ? renderAnswerExplainCard(trace)
            : renderExpressionCard(trace);
        if (card) container.appendChild(card);
      });
  }

  function renderExpressionCard(trace) {
    if (!trace) return null;
    const card = document.createElement("div");
    card.className = "explain-card";

    const header = document.createElement("div");
    header.className = "explain-header";

    const title = document.createElement("div");
    title.className = "explain-title";
    title.textContent = trace.target ? `${trace.target} =` : "Expression";

    const meta = document.createElement("div");
    meta.className = "explain-meta";
    const spanSummary = summarizeSpan(trace);
    meta.textContent = spanSummary || "";

    header.appendChild(title);
    if (meta.textContent) header.appendChild(meta);

    const actions = document.createElement("div");
    actions.className = "explain-actions";
    const jump = document.createElement("button");
    jump.type = "button";
    jump.className = "btn ghost";
    jump.textContent = "Show in Formulas";
    jump.onclick = () => jumpToFormula(trace);
    actions.appendChild(jump);

    const expr = document.createElement("pre");
    expr.className = "code-block explain-expression";
    expr.textContent = trace.expression || "";

    const result = document.createElement("div");
    result.className = "explain-result";
    const resultLabel = document.createElement("div");
    resultLabel.className = "inline-label";
    resultLabel.textContent = "Result";
    const resultValue = document.createElement("pre");
    resultValue.className = "code-block";
    resultValue.textContent = formatValue(trace.result);
    result.appendChild(resultLabel);
    result.appendChild(resultValue);

    const details = document.createElement("details");
    details.className = "explain-details";
    const summary = document.createElement("summary");
    summary.textContent = "Steps";
    const steps = document.createElement("pre");
    steps.className = "code-block";
    steps.textContent = formatSteps(trace.steps || []);
    details.appendChild(summary);
    details.appendChild(steps);

    card.appendChild(header);
    card.appendChild(actions);
    card.appendChild(expr);
    card.appendChild(result);
    card.appendChild(details);

    if (trace.truncated) {
      const note = document.createElement("div");
      note.className = "explain-note";
      note.textContent = "Trace truncated to keep output deterministic.";
      card.appendChild(note);
    }
    return card;
  }

  function renderAnswerExplainCard(trace) {
    const explainBundle = trace && trace.explain ? trace.explain : {};
    const card = document.createElement("div");
    card.className = "explain-card";

    const header = document.createElement("div");
    header.className = "explain-header";

    const title = document.createElement("div");
    title.className = "explain-title";
    title.textContent = "Answer explain";

    const meta = document.createElement("div");
    meta.className = "explain-meta";
    const mode = explainBundle.retrieval_mode || "auto";
    const count = Number(explainBundle.candidate_count) || 0;
    meta.textContent = `mode: ${mode} · candidates: ${count}`;

    header.appendChild(title);
    header.appendChild(meta);

    const summary = document.createElement("div");
    summary.className = "explain-result";
    const summaryLabel = document.createElement("div");
    summaryLabel.className = "inline-label";
    summaryLabel.textContent = "Summary";
    const summaryValue = document.createElement("pre");
    summaryValue.className = "code-block";
    summaryValue.textContent = formatAnswerSummary(explainBundle);
    summary.appendChild(summaryLabel);
    summary.appendChild(summaryValue);

    const details = document.createElement("details");
    details.className = "explain-details";
    const summaryTitle = document.createElement("summary");
    summaryTitle.textContent = "Candidates";
    const candidates = document.createElement("pre");
    candidates.className = "code-block";
    candidates.textContent = formatValue(explainBundle.candidates || []);
    details.appendChild(summaryTitle);
    details.appendChild(candidates);

    card.appendChild(header);
    card.appendChild(summary);
    card.appendChild(details);
    return card;
  }

  function formatAnswerSummary(explainBundle) {
    const validation = explainBundle.answer_validation || {};
    const lines = [
      `query: ${formatValue(explainBundle.query || "")}`,
      `retrieval_mode: ${formatValue(explainBundle.retrieval_mode || "auto")}`,
      `candidate_count: ${formatValue(explainBundle.candidate_count || 0)}`,
      `final_selection: ${formatList(explainBundle.final_selection)}`,
      `validation_status: ${formatValue(validation.status || "unknown")}`,
      `citation_count: ${formatValue(validation.citation_count || 0)}`,
      `unknown_citations: ${formatList(validation.unknown_citations)}`,
      `prompt_hash: ${formatValue(validation.prompt_hash || "")}`,
    ];
    return lines.join("\n");
  }

  function formatList(value) {
    if (!Array.isArray(value)) return "[]";
    if (!value.length) return "[]";
    return `[${value.map((item) => String(item)).join(", ")}]`;
  }

  explain.renderExplain = renderExplain;
  window.renderExplain = renderExplain;
})();
