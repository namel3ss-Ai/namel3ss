(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state || (root.state = {});

  let cachedManifest = null;
  let cachedData = null;
  let cachedSummary = null;
  let cachedDataStatus = null;
  let cachedMigrationStatus = null;
  let cachedMigrationPlan = null;
  let cachedTraces = [];
  let cachedSpans = [];
  let cachedLogs = [];
  let cachedMetrics = null;
  let cachedDiagnostics = null;
  let cachedLastRunError = null;
  let cachedFormulas = null;
  let cachedAgents = null;
  let cachedAgentRun = null;
  let cachedSession = null;
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
  function getCachedData() {
    return cachedData;
  }
  function setCachedData(value) {
    cachedData = value || null;
    return cachedData;
  }
  function getCachedSummary() {
    return cachedSummary;
  }
  function setCachedSummary(value) {
    cachedSummary = value || null;
    return cachedSummary;
  }
  function getCachedDataStatus() {
    return cachedDataStatus;
  }
  function setCachedDataStatus(value) {
    cachedDataStatus = value || null;
    return cachedDataStatus;
  }
  function getCachedMigrationStatus() {
    return cachedMigrationStatus;
  }
  function setCachedMigrationStatus(value) {
    cachedMigrationStatus = value || null;
    return cachedMigrationStatus;
  }
  function getCachedMigrationPlan() {
    return cachedMigrationPlan;
  }
  function setCachedMigrationPlan(value) {
    cachedMigrationPlan = value || null;
    return cachedMigrationPlan;
  }
  function getCachedTraces() {
    return cachedTraces;
  }
  function setCachedTraces(value) {
    cachedTraces = Array.isArray(value) ? value : cachedTraces;
    return cachedTraces;
  }
  function getCachedSpans() {
    return cachedSpans;
  }
  function setCachedSpans(value) {
    cachedSpans = Array.isArray(value) ? value : cachedSpans;
    return cachedSpans;
  }
  function getCachedLogs() {
    return cachedLogs;
  }
  function setCachedLogs(value) {
    cachedLogs = Array.isArray(value) ? value : cachedLogs;
    return cachedLogs;
  }
  function getCachedMetrics() {
    return cachedMetrics;
  }
  function setCachedMetrics(value) {
    cachedMetrics = value || null;
    return cachedMetrics;
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
  function getCachedFormulas() {
    return cachedFormulas;
  }
  function setCachedFormulas(value) {
    cachedFormulas = value || null;
    return cachedFormulas;
  }
  function getCachedAgents() {
    return cachedAgents;
  }
  function setCachedAgents(value) {
    cachedAgents = value || null;
    return cachedAgents;
  }
  function getCachedAgentRun() {
    return cachedAgentRun;
  }
  function setCachedAgentRun(value) {
    cachedAgentRun = value || null;
    return cachedAgentRun;
  }
  function getCachedSession() {
    return cachedSession;
  }
  function setCachedSession(value) {
    cachedSession = value || null;
    return cachedSession;
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
  state.getCachedData = getCachedData;
  state.setCachedData = setCachedData;
  state.getCachedSummary = getCachedSummary;
  state.setCachedSummary = setCachedSummary;
  state.getCachedDataStatus = getCachedDataStatus;
  state.setCachedDataStatus = setCachedDataStatus;
  state.getCachedMigrationStatus = getCachedMigrationStatus;
  state.setCachedMigrationStatus = setCachedMigrationStatus;
  state.getCachedMigrationPlan = getCachedMigrationPlan;
  state.setCachedMigrationPlan = setCachedMigrationPlan;
  state.getCachedTraces = getCachedTraces;
  state.setCachedTraces = setCachedTraces;
  state.getCachedSpans = getCachedSpans;
  state.setCachedSpans = setCachedSpans;
  state.getCachedLogs = getCachedLogs;
  state.setCachedLogs = setCachedLogs;
  state.getCachedMetrics = getCachedMetrics;
  state.setCachedMetrics = setCachedMetrics;
  state.getCachedDiagnostics = getCachedDiagnostics;
  state.setCachedDiagnostics = setCachedDiagnostics;
  state.getCachedLastRunError = getCachedLastRunError;
  state.setCachedLastRunError = setCachedLastRunError;
  state.getCachedFormulas = getCachedFormulas;
  state.setCachedFormulas = setCachedFormulas;
  state.getCachedAgents = getCachedAgents;
  state.setCachedAgents = setCachedAgents;
  state.getCachedAgentRun = getCachedAgentRun;
  state.setCachedAgentRun = setCachedAgentRun;
  state.getCachedSession = getCachedSession;
  state.setCachedSession = setCachedSession;
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
