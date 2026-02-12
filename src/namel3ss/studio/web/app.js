(() => {
  async function waitForRendererRegistry() {
    const registry = window.N3RendererRegistry;
    if (!registry || typeof registry !== "object") {
      throw new Error("Studio boot missing renderer registry.");
    }
    if (!registry.ready || typeof registry.ready.then !== "function") {
      throw new Error("Studio boot missing renderer registry readiness promise.");
    }
    await registry.ready;
  }

  function renderBootError(error) {
    const banner = document.getElementById("errorBanner");
    if (!banner) return;
    const stableCode =
      error &&
      typeof error === "object" &&
      typeof error.error_code === "string" &&
      error.error_code.trim()
        ? error.error_code.trim()
        : "";
    const message = error && error.message ? error.message : "Studio boot failed.";
    banner.textContent = stableCode ? `${stableCode}: ${message}` : message;
    banner.classList.remove("hidden");
  }

  async function boot() {
    await waitForRendererRegistry();
    const root = window.N3Studio || {};
    const missing = [];

    if (typeof window.renderUI !== "function") missing.push("renderUI");
    if (!root.refresh || typeof root.refresh.refreshUI !== "function") missing.push("refresh");
    if (!root.run || typeof root.run.setupRunButton !== "function") missing.push("run");
    if (!root.dock || typeof root.dock.setupDock !== "function") missing.push("dock");
    if (!root.preview || typeof root.preview.setupPreview !== "function") missing.push("preview");
    if (typeof window.renderData !== "function") missing.push("data");
    if (!root.menu || typeof root.menu.setupMenu !== "function") missing.push("menu");
    if (typeof window.renderTraces !== "function") missing.push("traces");
    if (typeof window.renderTracing !== "function") missing.push("tracing");
    if (typeof window.renderLogs !== "function") missing.push("logs");
    if (typeof window.renderMetrics !== "function") missing.push("metrics");
    if (typeof window.renderExplain !== "function") missing.push("explain");
    if (typeof window.renderDiagnostics !== "function") missing.push("diagnostics");
    if (typeof window.renderErrors !== "function") missing.push("errors");
    if (!root.formulas || typeof root.formulas.setupFormulas !== "function") missing.push("formulas");
    if (typeof window.renderFormulas !== "function") missing.push("formulas_render");
    if (typeof window.renderMemory !== "function") missing.push("memory");
    if (!root.agents || typeof root.agents.setupAgents !== "function") missing.push("agents");
    if (!root.setup || typeof root.setup.refreshSetup !== "function") missing.push("setup");
    if (typeof window.refreshGraphPanel !== "function") missing.push("graph");

    if (missing.length) {
      throw new Error(`Studio boot missing modules: ${missing.join(", ")}`);
    }

    root.run.setupRunButton();
    if (root.traces && root.traces.setupFilter) root.traces.setupFilter();
    if (root.preview && root.preview.setupPreview) root.preview.setupPreview();
    if (root.feedback && root.feedback.setupPreviewFeedback) root.feedback.setupPreviewFeedback();
    if (root.formulas && root.formulas.setupFormulas) root.formulas.setupFormulas();
    if (root.menu && root.menu.setupMenu) root.menu.setupMenu();
    if (root.agents && root.agents.setupAgents) root.agents.setupAgents();
    root.dock.setupDock();
    if (typeof window.renderErrors === "function") window.renderErrors();
    root.refresh.refreshUI();
    if (root.refresh && root.refresh.refreshSummary) root.refresh.refreshSummary();
    if (root.refresh && root.refresh.refreshDiagnostics) root.refresh.refreshDiagnostics();
  }

  function startBoot() {
    boot().catch((error) => {
      renderBootError(error);
      throw error;
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startBoot);
  } else {
    startBoot();
  }
})();
