(() => {
  const root = window.N3App || (window.N3App = {});
  const render = root.render || (root.render = {});
  const utils = root.utils;
  const state = root.state;

  function renderToolFixes(data, panel) {
    if (!panel) return;
    panel.innerHTML = "";
    const issues = data.issues || [];
    if (!issues.length) {
      panel.classList.add("hidden");
      return;
    }
    panel.classList.remove("hidden");
    const heading = document.createElement("div");
    heading.className = "inline-label";
    heading.textContent = "Fix suggestions";
    panel.appendChild(heading);
    const list = document.createElement("div");
    list.className = "list";
    issues.forEach((issue) => {
      const item = document.createElement("div");
      item.className = "list-item";
      const title = document.createElement("div");
      title.className = "list-title";
      const toolLabel = issue.tool_name ? ` (${issue.tool_name})` : "";
      title.textContent = `${issue.severity} ${issue.code}${toolLabel}`;
      const meta = document.createElement("div");
      meta.className = "list-meta";
      meta.textContent = issue.message || "See details.";
      item.appendChild(title);
      item.appendChild(meta);
      list.appendChild(item);
    });
    panel.appendChild(list);
  }

  function renderToolSection(container, title, items) {
    const heading = document.createElement("div");
    heading.className = "inline-label";
    heading.textContent = title;
    container.appendChild(heading);
    if (!items || items.length === 0) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = "No tools found.";
      container.appendChild(empty);
      return;
    }
    const list = document.createElement("div");
    list.className = "list";
    items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "list-item";
      const titleEl = document.createElement("div");
      titleEl.className = "list-title";
      titleEl.textContent = `${item.name} [${item.status}]`;
      const meta = document.createElement("div");
      meta.className = "list-meta";
      const parts = [];
      if (item.pack_id) parts.push(`pack: ${item.pack_id}`);
      if (item.source) parts.push(item.source);
      if (item.verified === false) parts.push("unverified");
      if (item.enabled === false) parts.push("disabled");
      if (item.entry) parts.push(`entry: ${item.entry}`);
      if (item.runner) parts.push(`runner: ${item.runner}`);
      if (item.kind) parts.push(`kind: ${item.kind}`);
      meta.textContent = parts.join(" \u00b7 ");
      row.appendChild(titleEl);
      if (parts.length) row.appendChild(meta);
      list.appendChild(row);
    });
    container.appendChild(list);
  }

  async function packAction(path, packId) {
    try {
      const resp = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pack_id: packId }),
      });
      const data = await resp.json();
      if (!data.ok) {
        utils.showToast(data.error || "Pack action failed.");
        return;
      }
      utils.showToast("Pack updated.");
      if (window.refreshAll) window.refreshAll();
    } catch (err) {
      utils.showToast("Pack action failed.");
    }
  }

  function renderTools(data) {
    state.setCachedTools(data || {});
    const container = document.getElementById("tools");
    if (!container) return;
    container.innerHTML = "";
    const fixPanel = document.getElementById("toolsFixPanel");
    if (!data || data.ok === false) {
      utils.showEmpty(container, data && data.error ? data.error : "Unable to load tools");
      utils.updateCopyButton("toolsCopy", () => "");
      if (fixPanel) fixPanel.classList.add("hidden");
      return;
    }
    renderToolFixes(data, fixPanel);
    const summary = data.summary || {};
    const summaryLine = document.createElement("div");
    summaryLine.className = "list-meta";
    summaryLine.textContent =
      `Summary: ok=${summary.ok || 0}, missing=${summary.missing || 0}, ` +
      `unused=${summary.unused || 0}, collisions=${summary.collisions || 0}, invalid=${summary.invalid || 0}.`;
    container.appendChild(summaryLine);

    if (data.bindings_valid === false && data.bindings_error) {
      const errorBox = document.createElement("div");
      errorBox.className = "empty-state";
      errorBox.textContent = data.bindings_error;
      container.appendChild(errorBox);
    }

    const filter = state.getToolsFilterText().trim().toLowerCase();
    const filterItems = (items) => {
      if (!filter) return items || [];
      return (items || []).filter((item) => (item.name || "").toLowerCase().includes(filter));
    };

    renderToolSection(container, "Pack tools", filterItems(data.packs));
    renderToolSection(container, "Declared tools", filterItems(data.declared));
    renderToolSection(container, "Bound tools", filterItems(data.bindings));

    utils.updateCopyButton("toolsCopy", () => JSON.stringify(data, null, 2));
  }

  render.renderToolFixes = renderToolFixes;
  render.renderToolSection = renderToolSection;
  render.packAction = packAction;
  render.renderTools = renderTools;
  window.renderTools = renderTools;
})();
