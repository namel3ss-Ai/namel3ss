(() => {
  const root = window.N3App || (window.N3App = {});
  const state = root.state;
  const setup = root.setup;
  const api = root.api;

  function boot() {
    setup.setupSeedButton();

    window.reselectElement = function () {
      if (!state.getSelectedElementId() || !state.getCachedManifest()) {
        renderInspector(null, null);
        return;
      }
      const match = findElementInManifest(state.getSelectedElementId());
      if (!match) {
        renderInspector(null, null);
        return;
      }
      state.setSelectedElement(match.element);
      state.setSelectedPage(match.page);
      renderInspector(state.getSelectedElement(), state.getSelectedPage());
      document.querySelectorAll(".ui-element").forEach((el) => {
        el.classList.toggle("selected", el.dataset.elementId === state.getSelectedElementId());
      });
    };
    setup.setupCoreButtons();
    setup.setupTabs();
    setup.setupTraceFilter();
    setup.setupTraceFormatToggle();
    setup.setupTracePhaseToggle();
    setup.setupTraceLaneToggle();
    setup.setupTraceMemoryFilters();
    setup.setupTraceModuleFilters();
    setup.setupTraceParallelFilters();
    setup.setupToolsFilter();
    api.loadVersion();
    setup.setupHelpModal();
    setup.setupToolsButtons();
    setup.setupPacksButtons();
    api.refreshAll();
  }

  root.boot = boot;
})();
