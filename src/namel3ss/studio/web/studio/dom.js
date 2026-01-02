(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom || (root.dom = {});
  const guidance = root.guidance || {};

  function buildEmpty(message) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = message;
    return empty;
  }

  function showEmpty(container, message) {
    if (!container) return;
    container.innerHTML = "";
    container.appendChild(buildEmpty(message));
  }

  function buildStatusLines(lines) {
    const wrapper = document.createElement("div");
    wrapper.className = "run-status-lines";
    (lines || []).forEach((line) => {
      const row = document.createElement("div");
      row.className = "status-line";
      row.textContent = line;
      wrapper.appendChild(row);
    });
    return wrapper;
  }

  function buildErrorLines(detail) {
    const lines = ["Couldn't run."];
    const rawText = redactText(_extractErrorText(detail));
    const parsed = guidance.parseGuidance ? guidance.parseGuidance(rawText) : { raw: rawText };
    const hasGuidance = Boolean(parsed && (parsed.what || parsed.why || parsed.fix || parsed.where || parsed.example));
    if (hasGuidance) {
      const what = parsed.what || rawText;
      lines.push(`What happened: ${what}`);
      if (parsed.where) lines.push(`Where: ${parsed.where}`);
      if (parsed.why) lines.push(`Why: ${parsed.why}`);
      if (parsed.fix) lines.push(`How to fix: ${parsed.fix}`);
      lines.push(`Try: ${parsed.example || "Run again."}`);
      return lines;
    }
    if (detail) {
      lines.push("What happened:");
      if (typeof detail === "string") {
        lines.push(detail);
      } else if (detail.error) {
        lines.push(detail.error);
      } else if (detail.message) {
        lines.push(detail.message);
      } else if (Array.isArray(detail.errors)) {
        const fieldLines = detail.errors
          .map((err) => {
            if (!err) return null;
            if (err.field && err.message) return `${err.field}: ${err.message}`;
            if (err.message) return err.message;
            return null;
          })
          .filter(Boolean);
        if (fieldLines.length) lines.push(fieldLines.join("; "));
      } else {
        try {
          lines.push(JSON.stringify(detail));
        } catch (err) {
          lines.push(String(detail));
        }
      }
    }
    lines.push("Try: Run again.");
    return lines;
  }

  function _extractErrorText(detail) {
    if (!detail) return "";
    if (typeof detail === "string") return detail;
    if (detail.error) return detail.error;
    if (detail.message) return detail.message;
    if (Array.isArray(detail.errors)) {
      const fieldLines = detail.errors
        .map((err) => {
          if (!err) return null;
          if (err.field && err.message) return `${err.field}: ${err.message}`;
          if (err.message) return err.message;
          return null;
        })
        .filter(Boolean);
      if (fieldLines.length) return fieldLines.join("; ");
    }
    try {
      return JSON.stringify(detail);
    } catch (err) {
      return String(detail);
    }
  }

  function redactText(text) {
    return String(text || "")
      .replace(/Bearer\s+[A-Za-z0-9._-]+/gi, "Bearer [redacted]")
      .replace(/sk-[A-Za-z0-9_-]+/g, "[redacted]");
  }

  function showError(container, detail) {
    if (!container) return;
    container.innerHTML = "";
    const empty = buildEmpty("");
    empty.classList.add("status-error");
    const lines = buildErrorLines(detail);
    empty.appendChild(buildStatusLines(lines));
    container.appendChild(empty);
  }

  dom.buildEmpty = buildEmpty;
  dom.showEmpty = showEmpty;
  dom.buildStatusLines = buildStatusLines;
  dom.buildErrorLines = buildErrorLines;
  dom.showError = showError;

  window.showEmpty = showEmpty;
  window.showError = showError;
})();
