(() => {
  const root = window.N3App || (window.N3App = {});
  const setup = root.setup || (root.setup = {});
  const state = root.state;

  function setupTraceFormatToggle() {
    const plainBtn = document.getElementById("traceFormatPlain");
    const jsonBtn = document.getElementById("traceFormatJson");
    if (!plainBtn || !jsonBtn) return;
    const applyMode = (mode) => {
      state.setTraceRenderMode(mode);
      plainBtn.classList.toggle("toggle-active", mode === "plain");
      jsonBtn.classList.toggle("toggle-active", mode === "json");
      plainBtn.setAttribute("aria-pressed", mode === "plain");
      jsonBtn.setAttribute("aria-pressed", mode === "json");
      if (window.renderTraces) window.renderTraces(state.getCachedTraces());
    };
    plainBtn.onclick = () => applyMode("plain");
    jsonBtn.onclick = () => applyMode("json");
    applyMode(state.getTraceRenderMode() || "plain");
  }

  function setupTracePhaseToggle() {
    const currentBtn = document.getElementById("tracePhaseCurrent");
    const historyBtn = document.getElementById("tracePhaseHistory");
    if (!currentBtn || !historyBtn) return;
    const applyMode = (mode) => {
      state.setTracePhaseMode(mode);
      currentBtn.classList.toggle("toggle-active", mode === "current");
      historyBtn.classList.toggle("toggle-active", mode === "history");
      currentBtn.setAttribute("aria-pressed", mode === "current");
      historyBtn.setAttribute("aria-pressed", mode === "history");
      if (window.renderTraces) window.renderTraces(state.getCachedTraces());
    };
    currentBtn.onclick = () => applyMode("current");
    historyBtn.onclick = () => applyMode("history");
    applyMode(state.getTracePhaseMode() || "current");
  }

  function setupTraceLaneToggle() {
    const myBtn = document.getElementById("traceLaneMy");
    const teamBtn = document.getElementById("traceLaneTeam");
    const systemBtn = document.getElementById("traceLaneSystem");
    if (!myBtn || !teamBtn || !systemBtn) return;
    const applyMode = (mode) => {
      state.setTraceLaneMode(mode);
      myBtn.classList.toggle("toggle-active", mode === "my");
      teamBtn.classList.toggle("toggle-active", mode === "team");
      systemBtn.classList.toggle("toggle-active", mode === "system");
      myBtn.setAttribute("aria-pressed", mode === "my");
      teamBtn.setAttribute("aria-pressed", mode === "team");
      systemBtn.setAttribute("aria-pressed", mode === "system");
      if (window.renderTraces) window.renderTraces(state.getCachedTraces());
      if (window.refreshAgreements) window.refreshAgreements();
    };
    myBtn.onclick = () => applyMode("my");
    teamBtn.onclick = () => applyMode("team");
    systemBtn.onclick = () => applyMode("system");
    applyMode(state.getTraceLaneMode() || "my");
  }

  function setupTraceMemoryFilters() {
    const entries = [
      { id: "traceMemoryBudget", type: "memory_budget" },
      { id: "traceMemoryCompaction", type: "memory_compaction" },
      { id: "traceMemoryCacheHit", type: "memory_cache_hit" },
      { id: "traceMemoryCacheMiss", type: "memory_cache_miss" },
      { id: "traceMemoryWakeUp", type: "memory_wake_up_report" },
      { id: "traceMemoryRestoreFailed", type: "memory_restore_failed" },
      { id: "traceMemoryPackLoaded", type: "memory_pack_loaded" },
      { id: "traceMemoryPackMerged", type: "memory_pack_merged" },
      { id: "traceMemoryPackOverrides", type: "memory_pack_overrides" },
    ];
    const buttons = entries
      .map((entry) => ({ entry, btn: document.getElementById(entry.id) }))
      .filter((entry) => entry.btn);
    if (!buttons.length) return;

    const updateButtons = () => {
      const filters = state.getMemoryBudgetFilters() || {};
      buttons.forEach(({ entry, btn }) => {
        const enabled = filters[entry.type] !== false;
        btn.classList.toggle("toggle-active", enabled);
        btn.setAttribute("aria-pressed", enabled ? "true" : "false");
      });
    };
    buttons.forEach(({ entry, btn }) => {
      btn.onclick = () => {
        const filters = state.getMemoryBudgetFilters() || {};
        const enabled = filters[entry.type] !== false;
        state.setMemoryBudgetFilter(entry.type, !enabled);
        updateButtons();
        if (window.renderTraces) window.renderTraces(state.getCachedTraces());
      };
    });
    updateButtons();
  }

  function setupTraceModuleFilters() {
    const entries = [
      { id: "traceModuleLoaded", type: "module_loaded" },
      { id: "traceModuleMerged", type: "module_merged" },
      { id: "traceModuleOverrides", type: "module_overrides" },
    ];
    const buttons = entries
      .map((entry) => ({ entry, btn: document.getElementById(entry.id) }))
      .filter((entry) => entry.btn);
    if (!buttons.length) return;

    const updateButtons = () => {
      const filters = state.getModuleTraceFilters() || {};
      buttons.forEach(({ entry, btn }) => {
        const enabled = filters[entry.type] !== false;
        btn.classList.toggle("toggle-active", enabled);
        btn.setAttribute("aria-pressed", enabled ? "true" : "false");
      });
    };
    buttons.forEach(({ entry, btn }) => {
      btn.onclick = () => {
        const filters = state.getModuleTraceFilters() || {};
        const enabled = filters[entry.type] !== false;
        state.setModuleTraceFilter(entry.type, !enabled);
        updateButtons();
        if (window.renderTraces) window.renderTraces(state.getCachedTraces());
      };
    });
    updateButtons();
  }

  function setupTraceParallelFilters() {
    const entries = [
      { id: "traceParallelStarted", type: "parallel_started" },
      { id: "traceParallelTaskFinished", type: "parallel_task_finished" },
      { id: "traceParallelMerged", type: "parallel_merged" },
    ];
    const buttons = entries
      .map((entry) => ({ entry, btn: document.getElementById(entry.id) }))
      .filter((entry) => entry.btn);
    if (!buttons.length) return;

    const updateButtons = () => {
      const filters = state.getParallelTraceFilters() || {};
      buttons.forEach(({ entry, btn }) => {
        const enabled = filters[entry.type] !== false;
        btn.classList.toggle("toggle-active", enabled);
        btn.setAttribute("aria-pressed", enabled ? "true" : "false");
      });
    };
    buttons.forEach(({ entry, btn }) => {
      btn.onclick = () => {
        const filters = state.getParallelTraceFilters() || {};
        const enabled = filters[entry.type] !== false;
        state.setParallelTraceFilter(entry.type, !enabled);
        updateButtons();
        if (window.renderTraces) window.renderTraces(state.getCachedTraces());
      };
    });
    updateButtons();
  }

  setup.setupTraceFormatToggle = setupTraceFormatToggle;
  setup.setupTracePhaseToggle = setupTracePhaseToggle;
  setup.setupTraceLaneToggle = setupTraceLaneToggle;
  setup.setupTraceMemoryFilters = setupTraceMemoryFilters;
  setup.setupTraceModuleFilters = setupTraceModuleFilters;
  setup.setupTraceParallelFilters = setupTraceParallelFilters;
})();
