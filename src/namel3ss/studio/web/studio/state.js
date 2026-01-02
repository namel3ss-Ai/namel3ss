(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state || (root.state = {});

  let cachedManifest = null;
  let cachedSummary = null;
  let cachedTraces = [];
  let cachedDiagnostics = null;
  let cachedLastRunError = null;
  let seedActionId = null;
  let resetActionId = null;
  let lastAction = null;
  let themeSetting = "system";
  let runtimeTheme = null;

  function setThemeGlobals() {
    window.themeSetting = themeSetting;
    window.runtimeTheme = runtimeTheme;
  }

  function getCachedManifest() {
    return cachedManifest;
  }
  function setCachedManifest(value) {
    cachedManifest = value || null;
    return cachedManifest;
  }
  function getCachedSummary() {
    return cachedSummary;
  }
  function setCachedSummary(value) {
    cachedSummary = value || null;
    return cachedSummary;
  }
  function getCachedTraces() {
    return cachedTraces;
  }
  function setCachedTraces(value) {
    cachedTraces = Array.isArray(value) ? value : cachedTraces;
    return cachedTraces;
  }
  function getCachedDiagnostics() {
    return cachedDiagnostics;
  }
  function setCachedDiagnostics(value) {
    cachedDiagnostics = value || null;
    return cachedDiagnostics;
  }
  function getCachedLastRunError() {
    return cachedLastRunError;
  }
  function setCachedLastRunError(value) {
    cachedLastRunError = value || null;
    return cachedLastRunError;
  }
  function getSeedActionId() {
    return seedActionId;
  }
  function setSeedActionId(value) {
    seedActionId = value || null;
    return seedActionId;
  }
  function getResetActionId() {
    return resetActionId;
  }
  function setResetActionId(value) {
    resetActionId = value || null;
    return resetActionId;
  }
  function getLastAction() {
    return lastAction;
  }
  function setLastAction(value) {
    lastAction = value || null;
    return lastAction;
  }
  function getThemeSetting() {
    return themeSetting;
  }
  function setThemeSetting(value) {
    themeSetting = value || "system";
    setThemeGlobals();
    return themeSetting;
  }
  function getRuntimeTheme() {
    return runtimeTheme;
  }
  function setRuntimeTheme(value) {
    runtimeTheme = value || null;
    setThemeGlobals();
    return runtimeTheme;
  }

  setThemeGlobals();

  state.getCachedManifest = getCachedManifest;
  state.setCachedManifest = setCachedManifest;
  state.getCachedSummary = getCachedSummary;
  state.setCachedSummary = setCachedSummary;
  state.getCachedTraces = getCachedTraces;
  state.setCachedTraces = setCachedTraces;
  state.getCachedDiagnostics = getCachedDiagnostics;
  state.setCachedDiagnostics = setCachedDiagnostics;
  state.getCachedLastRunError = getCachedLastRunError;
  state.setCachedLastRunError = setCachedLastRunError;
  state.getSeedActionId = getSeedActionId;
  state.setSeedActionId = setSeedActionId;
  state.getResetActionId = getResetActionId;
  state.setResetActionId = setResetActionId;
  state.getLastAction = getLastAction;
  state.setLastAction = setLastAction;
  state.getThemeSetting = getThemeSetting;
  state.setThemeSetting = setThemeSetting;
  state.getRuntimeTheme = getRuntimeTheme;
  state.setRuntimeTheme = setRuntimeTheme;
})();
