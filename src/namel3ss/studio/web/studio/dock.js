(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dock = root.dock || (root.dock = {});

  let activeTab = null;

  function runPanelHook(tabName) {
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
    }
  }

  function setupDock() {
    const tabs = Array.from(document.querySelectorAll(".dock .tab"));
    const panels = Array.from(document.querySelectorAll(".panel[data-tab]"));
    const sheet = document.getElementById("sheet");
    const backdrop = document.getElementById("sheetBackdrop");

    if (!tabs.length || !sheet || !backdrop) return;

    const setActive = (name) => {
      activeTab = name || null;
      tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === activeTab));
      panels.forEach((panel) => panel.classList.toggle("active", panel.dataset.tab === activeTab));
      sheet.classList.toggle("hidden", !activeTab);
      backdrop.classList.toggle("hidden", !activeTab);
      if (activeTab) runPanelHook(activeTab);
    };

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const name = tab.dataset.tab;
        if (name === activeTab) {
          setActive(null);
        } else {
          setActive(name);
        }
      });
    });

    backdrop.addEventListener("click", () => setActive(null));
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") setActive(null);
    });

    setActive(null);
  }

  dock.setupDock = setupDock;
})();
