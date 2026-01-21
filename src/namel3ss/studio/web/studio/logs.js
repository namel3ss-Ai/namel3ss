(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const dom = root.dom;
  const net = root.net;
  const logs = root.logs || (root.logs = {});

  function getContainer() {
    return document.getElementById("logs");
  }

  function formatMeta(entry) {
    const parts = [];
    if (entry.id) parts.push(String(entry.id));
    if (entry.span_id) parts.push(String(entry.span_id));
    return parts.join(" | ");
  }

  function buildLogRow(entry) {
    const row = document.createElement("div");
    const level = String(entry.level || "info");
    row.className = `log-row log-level-${level}`;

    const header = document.createElement("div");
    header.className = "log-header";

    const levelEl = document.createElement("div");
    levelEl.className = "log-level";
    levelEl.textContent = level.toUpperCase();

    const message = document.createElement("div");
    message.className = "log-message";
    message.textContent = entry.message || "";

    const meta = document.createElement("div");
    meta.className = "log-meta";
    meta.textContent = formatMeta(entry);

    header.appendChild(levelEl);
    header.appendChild(message);
    if (meta.textContent) header.appendChild(meta);
    row.appendChild(header);

    const fields = entry.fields && typeof entry.fields === "object" ? entry.fields : null;
    if (fields && Object.keys(fields).length) {
      const block = document.createElement("pre");
      block.className = "log-fields";
      block.textContent = JSON.stringify(fields, null, 2);
      row.appendChild(block);
    }
    return row;
  }

  function renderLogs(input) {
    const container = getContainer();
    if (!container) return;
    const list = Array.isArray(input)
      ? input
      : (state && typeof state.getCachedLogs === "function" ? state.getCachedLogs() : []);
    const logsList = Array.isArray(list) ? list : [];
    if (!logsList.length) {
      dom.showEmpty(container, "No logs yet. Run your app.");
      return;
    }
    container.innerHTML = "";
    logsList.forEach((entry) => {
      if (!entry || typeof entry !== "object") return;
      container.appendChild(buildLogRow(entry));
    });
  }

  async function refreshLogs() {
    if (!net || typeof net.fetchJson !== "function") return;
    try {
      const payload = await net.fetchJson("/api/logs");
      const entries = payload && Array.isArray(payload.logs) ? payload.logs : [];
      if (state && typeof state.setCachedLogs === "function") {
        state.setCachedLogs(entries);
      }
      renderLogs(entries);
    } catch (_err) {
      renderLogs([]);
    }
  }

  logs.renderLogs = renderLogs;
  logs.refreshLogs = refreshLogs;
  window.renderLogs = renderLogs;
})();
