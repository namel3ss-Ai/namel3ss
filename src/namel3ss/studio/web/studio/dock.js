(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dock = root.dock || (root.dock = {});

  let activeTab = "preview";

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
    if (tabName === "memory" && typeof window.renderMemory === "function") {
      window.renderMemory();
      return;
    }
    if (tabName === "why" && typeof window.refreshWhyPanel === "function") {
      window.refreshWhyPanel();
      return;
    }
    if (tabName === "data" && typeof window.renderData === "function") {
      window.renderData();
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

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const name = tab.dataset.tab;
        setActive(name);
      });
    });

    if (!tabs.length || !modes.length) return;
    setActive(activeTab || "preview");
  }

  dock.setupDock = setupDock;
})();
