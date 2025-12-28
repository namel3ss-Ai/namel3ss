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

  setup.setupTraceFormatToggle = setupTraceFormatToggle;
  setup.setupTracePhaseToggle = setupTracePhaseToggle;
  setup.setupTraceLaneToggle = setupTraceLaneToggle;
})();
