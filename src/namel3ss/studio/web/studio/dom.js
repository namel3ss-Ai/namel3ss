(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom || (root.dom = {});

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
