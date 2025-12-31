(() => {
  function boot() {
    const root = window.N3Studio || {};
    const missing = [];

    if (typeof window.renderUI !== "function") missing.push("renderUI");
    if (!root.refresh || typeof root.refresh.refreshUI !== "function") missing.push("refresh");
    if (!root.run || typeof root.run.setupRunButton !== "function") missing.push("run");
    if (!root.dock || typeof root.dock.setupDock !== "function") missing.push("dock");
    if (typeof window.renderTraces !== "function") missing.push("traces");
    if (typeof window.renderMemory !== "function") missing.push("memory");
    if (typeof window.refreshGraphPanel !== "function") missing.push("graph");

    if (missing.length) {
      throw new Error(`Studio boot missing modules: ${missing.join(", ")}`);
    }

    root.run.setupRunButton();
    if (root.traces && root.traces.setupFilter) root.traces.setupFilter();
    root.dock.setupDock();
    root.refresh.refreshUI();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
