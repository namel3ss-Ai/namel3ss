(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const dom = root.dom;
  const net = root.net;
  const formulas = root.formulas || (root.formulas = {});

  let viewMode = "code";

  function getContainer() {
    return document.getElementById("formulas");
  }

  function getToggleButtons() {
    return Array.from(document.querySelectorAll("[data-formula-view]"));
  }

  function setViewMode(mode) {
    viewMode = mode === "formula" ? "formula" : "code";
    updateToggle();
    renderFormulas();
  }

  function updateToggle() {
    getToggleButtons().forEach((button) => {
      const isActive = button.dataset.formulaView === viewMode;
      button.classList.toggle("active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });
  }

  function setupFormulas() {
    getToggleButtons().forEach((button) => {
      button.addEventListener("click", () => setViewMode(button.dataset.formulaView));
    });
    updateToggle();
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text || "");
      return;
    }
    const textarea = document.createElement("textarea");
    textarea.value = text || "";
    textarea.setAttribute("readonly", "true");
    textarea.style.position = "absolute";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }

  function resolveErrorLocation() {
    if (!state) return null;
    const last = state.getCachedLastRunError ? state.getCachedLastRunError() : null;
    if (last && last.location && last.location.line) {
      return {
        line: last.location.line,
        message: last.error || last.message || "Error",
      };
    }
    const summary = state.getCachedSummary ? state.getCachedSummary() : null;
    if (summary && summary.ok === false && summary.location && summary.location.line) {
      return {
        line: summary.location.line,
        message: summary.error || summary.message || "Parse error",
      };
    }
    return null;
  }

  function assignmentHasError(assignment, error) {
    if (!error || !assignment) return false;
    const start = assignment.line_start || 0;
    const end = assignment.line_end || start;
    const line = error.line || 0;
    return line >= start && line <= end;
  }

  function renderFormulaRhs(text) {
    if (!text || !text.includes("**")) {
      const span = document.createElement("span");
      span.textContent = text || "";
      return span;
    }
    const wrapper = document.createElement("span");
    const pattern = /([A-Za-z0-9_.\)\]]+)\s*\*\*\s*([A-Za-z0-9_.\(\[]+)/g;
    let cursor = 0;
    let match = null;
    while ((match = pattern.exec(text)) !== null) {
      const prefix = text.slice(cursor, match.index);
      if (prefix) {
        wrapper.appendChild(document.createTextNode(prefix));
      }
      const power = document.createElement("span");
      power.className = "formula-power";
      const base = document.createElement("span");
      base.textContent = match[1];
      const exp = document.createElement("sup");
      exp.textContent = match[2];
      power.appendChild(base);
      power.appendChild(exp);
      wrapper.appendChild(power);
      cursor = match.index + match[0].length;
    }
    const tail = text.slice(cursor);
    if (tail) wrapper.appendChild(document.createTextNode(tail));
    return wrapper;
  }

  function renderFormulaAssignment(assignment, error) {
    const row = document.createElement("div");
    row.className = "formula-row";
    if (assignment && assignment.line_start) {
      row.dataset.lineStart = String(assignment.line_start);
    }
    const isError = assignmentHasError(assignment, error);
    if (isError) row.classList.add("error");

    const rowHeader = document.createElement("div");
    rowHeader.className = "formula-row-header";

    const expr = document.createElement("div");
    expr.className = "formula-expression";
    const lhs = document.createElement("span");
    lhs.className = "formula-lhs";
    lhs.textContent = assignment.lhs || "";
    const eq = document.createElement("span");
    eq.className = "formula-equals";
    eq.textContent = "=";
    const rhs = document.createElement("span");
    rhs.className = "formula-rhs";
    rhs.appendChild(renderFormulaRhs(assignment.rhs || ""));
    expr.appendChild(lhs);
    expr.appendChild(eq);
    expr.appendChild(rhs);

    const actions = document.createElement("div");
    actions.className = "formula-actions";
    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "btn ghost";
    copy.textContent = "Copy";
    copy.onclick = () => copyText(assignment.code || "");
    actions.appendChild(copy);

    rowHeader.appendChild(expr);
    rowHeader.appendChild(actions);
    row.appendChild(rowHeader);

    if (assignment.body && assignment.body.length) {
      const body = document.createElement("div");
      body.className = "formula-body";
      assignment.body.forEach((line) => {
        const bodyLine = document.createElement("div");
        bodyLine.className = "formula-body-line";
        bodyLine.textContent = line;
        body.appendChild(bodyLine);
      });
      row.appendChild(body);
    }

    if (isError && error && error.message) {
      const message = document.createElement("div");
      message.className = "formula-error";
      message.textContent = error.message;
      row.appendChild(message);
    }

    return row;
  }

  function renderCodeAssignment(assignment) {
    const pre = document.createElement("pre");
    pre.className = "code-block";
    if (assignment && assignment.line_start) {
      pre.dataset.lineStart = String(assignment.line_start);
    }
    pre.textContent = assignment.code || "";
    return pre;
  }

  function highlightLine(line) {
    const container = getContainer();
    if (!container || !line) return;
    const target = container.querySelector(`[data-line-start=\"${line}\"]`);
    if (!target) return;
    target.classList.add("formula-highlight");
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    window.setTimeout(() => target.classList.remove("formula-highlight"), 1600);
  }

  function renderBlock(block, error) {
    const wrapper = document.createElement("div");
    wrapper.className = "formula-block";
    const header = document.createElement("div");
    header.className = "formula-block-header";
    const flow = block.flow ? `flow "${block.flow}"` : "calc block";
    const line = block.line ? `line ${block.line}` : null;
    header.textContent = line ? `${flow} · ${line}` : flow;
    wrapper.appendChild(header);

    const assignments = Array.isArray(block.assignments) ? block.assignments : [];
    assignments.forEach((assignment) => {
      const node =
        viewMode === "formula"
          ? renderFormulaAssignment(assignment, error)
          : renderCodeAssignment(assignment);
      wrapper.appendChild(node);
    });
    return wrapper;
  }

  function renderFormulas(payload) {
    const container = getContainer();
    if (!container) return;
    const data = payload || (state && state.getCachedFormulas ? state.getCachedFormulas() : null);
    if (!data) {
      if (net && net.fetchJson) {
        refreshFormulas();
        return;
      }
      dom.showEmpty(container, "No formulas yet.");
      return;
    }
    if (data.ok === false) {
      dom.showError(container, data.error || "Unable to load formulas.");
      return;
    }
    const blocks = Array.isArray(data.blocks) ? data.blocks : [];
    if (!blocks.length) {
      dom.showEmpty(container, "No calc blocks found.");
      return;
    }
    container.innerHTML = "";
    const error = resolveErrorLocation();
    blocks.forEach((block) => {
      container.appendChild(renderBlock(block, error));
    });
  }

  async function refreshFormulas() {
    const container = getContainer();
    if (!container || !net || typeof net.fetchJson !== "function") return;
    try {
      const payload = await net.fetchJson("/api/formulas");
      if (state && typeof state.setCachedFormulas === "function") {
        state.setCachedFormulas(payload);
      }
      renderFormulas(payload);
    } catch (err) {
      const message = err && err.message ? err.message : "Unable to load formulas.";
      dom.showError(container, message);
    }
  }

  formulas.setupFormulas = setupFormulas;
  formulas.highlightLine = highlightLine;
  formulas.renderFormulas = renderFormulas;
  formulas.refreshFormulas = refreshFormulas;

  window.renderFormulas = renderFormulas;
  window.highlightFormulaLine = highlightLine;
})();
