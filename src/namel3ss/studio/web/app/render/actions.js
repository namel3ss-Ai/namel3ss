(() => {
  const root = window.N3App || (window.N3App = {});
  const render = root.render || (root.render = {});
  const utils = root.utils;
  const state = root.state;

  function renderActions(data) {
    state.setCachedActions(data || {});
    const container = document.getElementById("actions");
    if (!container) return;
    container.innerHTML = "";
    if (!data || data.ok === false) {
      utils.showEmpty(container, data && data.error ? data.error : "Unable to load actions");
      utils.updateCopyButton("actionsCopy", () => "");
      return;
    }
    const actions = data.actions || [];
    if (!actions.length) {
      utils.showEmpty(container, "No actions available.");
    } else {
      const list = document.createElement("div");
      list.className = "list";
      actions.forEach((action) => {
        const metaParts = [`type: ${action.type}`];
        if (action.flow) metaParts.push(`flow: ${action.flow}`);
        if (action.record) metaParts.push(`record: ${action.record}`);
        const item = document.createElement("div");
        item.className = "list-item";
        item.innerHTML = `<div class=\"list-title\">${action.id}</div><div class=\"list-meta\">${metaParts.join(" \u00b7 ")}</div>`;
        list.appendChild(item);
      });
      container.appendChild(list);
    }
    utils.updateCopyButton("actionsCopy", () => JSON.stringify(data, null, 2));
  }

  render.renderActions = renderActions;
  window.renderActions = renderActions;
})();
