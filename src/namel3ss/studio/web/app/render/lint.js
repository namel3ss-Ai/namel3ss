(() => {
  const root = window.N3App || (window.N3App = {});
  const render = root.render || (root.render = {});
  const utils = root.utils;
  const state = root.state;

  function renderLint(data) {
    state.setCachedLint(data || {});
    const container = document.getElementById("lint");
    if (!container) return;
    container.innerHTML = "";
    if (!data) {
      utils.showEmpty(container, "Unable to load lint findings");
      utils.updateCopyButton("lintCopy", () => "");
      return;
    }
    const findings = data.findings || [];
    if (findings.length === 0) {
      const ok = document.createElement("div");
      ok.className = "empty-state";
      ok.textContent = "OK";
      container.appendChild(ok);
    } else {
      const list = document.createElement("div");
      list.className = "list";
      findings.forEach((f) => {
        const item = document.createElement("div");
        item.className = "list-item";
        item.innerHTML = `<div class=\"list-title\">${f.severity} ${f.code}</div><div class=\"list-meta\">${f.message} (${f.line}:${f.column})</div>`;
        list.appendChild(item);
      });
      container.appendChild(list);
    }
    utils.updateCopyButton("lintCopy", () => JSON.stringify(data, null, 2));
  }

  render.renderLint = renderLint;
  window.renderLint = renderLint;
})();
