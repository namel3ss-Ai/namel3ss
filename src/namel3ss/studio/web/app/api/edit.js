(() => {
  const root = window.N3App || (window.N3App = {});
  const api = root.api || (root.api = {});
  const state = root.state;
  const utils = root.utils;

  async function performEdit(op, elementId, pageName, value, targetExtras = {}) {
    const res = await fetch("/api/edit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ op, target: { element_id: elementId, page: pageName, ...targetExtras }, value }),
    });
    const data = await res.json();
    if (!data.ok) {
      utils.showToast(data.error || "Edit failed");
      return;
    }
    if (window.renderSummary) window.renderSummary(data.summary);
    if (window.renderActions) window.renderActions(data.actions);
    if (window.renderLint) window.renderLint(data.lint);
    if (data.ui) {
      state.setCachedManifest(data.ui);
      if (window.renderUI) window.renderUI(data.ui);
    }
    if (window.reselectElement) window.reselectElement();
  }

  api.performEdit = performEdit;
  window.performEdit = performEdit;
})();
