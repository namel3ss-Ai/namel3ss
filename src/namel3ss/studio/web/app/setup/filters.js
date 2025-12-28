(() => {
  const root = window.N3App || (window.N3App = {});
  const setup = root.setup || (root.setup = {});
  const state = root.state;

  function setupTraceFilter() {
    const input = document.getElementById("tracesFilter");
    if (!input) return;
    input.addEventListener("input", () => {
      const timer = state.getTraceFilterTimer();
      if (timer) clearTimeout(timer);
      state.setTraceFilterTimer(
        setTimeout(() => {
          state.setTraceFilterText(input.value.trim().toLowerCase());
          if (window.renderTraces) window.renderTraces(state.getCachedTraces());
        }, 120)
      );
    });
  }

  function setupToolsFilter() {
    const input = document.getElementById("toolsFilter");
    if (!input) return;
    input.addEventListener("input", () => {
      const timer = state.getToolsFilterTimer();
      if (timer) clearTimeout(timer);
      state.setToolsFilterTimer(
        setTimeout(() => {
          state.setToolsFilterText(input.value.trim().toLowerCase());
          if (window.renderTools) window.renderTools(state.getCachedTools());
        }, 120)
      );
    });
  }

  setup.setupTraceFilter = setupTraceFilter;
  setup.setupToolsFilter = setupToolsFilter;
})();
