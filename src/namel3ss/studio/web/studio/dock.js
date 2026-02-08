(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dock = root.dock || (root.dock = {});

  let activeTab = "preview";
  let activateTab = null;

  function runPanelHook(tabName) {
    if (tabName === "preview" && root.preview && root.preview.applyManifest) {
      root.preview.applyManifest(root.state && root.state.getCachedManifest ? root.state.getCachedManifest() : null);
      return;
    }
    if (tabName === "graph" && typeof window.refreshGraphPanel === "function") {
      window.refreshGraphPanel();
      return;
    }
    if (tabName === "traces" && typeof window.renderTraces === "function") {
      window.renderTraces();
      return;
    }
    if (tabName === "tracing" && typeof window.renderTracing === "function") {
      window.renderTracing();
      return;
    }
    if (tabName === "logs" && typeof window.renderLogs === "function") {
      window.renderLogs();
      return;
    }
    if (tabName === "metrics" && typeof window.renderMetrics === "function") {
      window.renderMetrics();
      return;
    }
    if (tabName === "explain" && typeof window.renderExplain === "function") {
      window.renderExplain();
      return;
    }
    if (tabName === "diagnostics" && typeof window.renderDiagnostics === "function") {
      window.renderDiagnostics();
      return;
    }
    if (tabName === "errors" && typeof window.renderErrors === "function") {
      window.renderErrors();
      return;
    }
    if (tabName === "formulas" && typeof window.renderFormulas === "function") {
      window.renderFormulas();
      return;
    }
    if (tabName === "memory" && typeof window.renderMemory === "function") {
      window.renderMemory();
      return;
    }
    if (tabName === "agents" && root.agents && typeof root.agents.refreshAgents === "function") {
      root.agents.refreshAgents();
      return;
    }
    if (tabName === "registry" && root.registry && typeof root.registry.renderRegistry === "function") {
      root.registry.renderRegistry();
      return;
    }
    if (tabName === "console" && root.console && typeof root.console.renderConsole === "function") {
      root.console.renderConsole();
      return;
    }
    if (tabName === "feedback" && root.feedback && typeof root.feedback.renderFeedback === "function") {
      root.feedback.renderFeedback();
      return;
    }
    if (tabName === "canary" && root.canary && typeof root.canary.renderCanary === "function") {
      root.canary.renderCanary();
      return;
    }
    if (tabName === "marketplace" && root.marketplace && typeof root.marketplace.renderMarketplace === "function") {
      root.marketplace.renderMarketplace();
      return;
    }
    if (tabName === "tutorials" && root.tutorials && typeof root.tutorials.renderTutorials === "function") {
      root.tutorials.renderTutorials();
      return;
    }
    if (tabName === "playground" && root.playground && typeof root.playground.renderPlayground === "function") {
      root.playground.renderPlayground();
      return;
    }
    if (tabName === "versioning" && root.versioning && typeof root.versioning.renderVersioning === "function") {
      root.versioning.renderVersioning();
      return;
    }
    if (tabName === "quality" && root.quality && typeof root.quality.renderQuality === "function") {
      root.quality.renderQuality();
      return;
    }
    if (tabName === "mlops" && root.mlops && typeof root.mlops.renderMLOps === "function") {
      root.mlops.renderMLOps();
      return;
    }
    if (tabName === "triggers" && root.triggers && typeof root.triggers.renderTriggers === "function") {
      root.triggers.renderTriggers();
      return;
    }
    if (tabName === "deploy" && root.deploy && typeof root.deploy.renderDeploy === "function") {
      root.deploy.renderDeploy();
      return;
    }
    if (tabName === "why" && typeof window.refreshWhyPanel === "function") {
      window.refreshWhyPanel();
      return;
    }
    if (tabName === "data" && typeof window.renderData === "function") {
      window.renderData();
      return;
    }
    if (tabName === "setup" && root.setup && typeof root.setup.refreshSetup === "function") {
      root.setup.refreshSetup();
    }
  }

  function setupDock() {
    const tabs = Array.from(document.querySelectorAll(".dock .tab"));
    const modes = Array.from(document.querySelectorAll(".canvas-mode"));

    const setActive = (name) => {
      activeTab = name || null;
      tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === activeTab));
      modes.forEach((mode) => mode.classList.toggle("active", mode.dataset.mode === activeTab));
      if (activeTab) runPanelHook(activeTab);
    };
    activateTab = setActive;

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const name = tab.dataset.tab;
        setActive(name);
      });
    });

    if (!tabs.length || !modes.length) return;
    setActive(activeTab || "preview");
  }

  function setActiveTab(name) {
    if (activateTab) {
      activateTab(name);
    }
  }

  dock.setupDock = setupDock;
  dock.setActiveTab = setActiveTab;
})();
