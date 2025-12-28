(() => {
  const root = window.N3App || (window.N3App = {});
  const state = root.state || (root.state = {});
  const global = window;
  const defaults = {
    cachedSummary: {},
    cachedState: {},
    cachedActions: {},
    cachedTraces: [],
    cachedAgreements: {},
    cachedRules: {},
    cachedHandoffs: {},
    cachedLint: {},
    cachedTools: {},
    cachedPacks: {},
    cachedSecurity: {},
    cachedManifest: null,
    traceFilterText: "",
    memoryBudgetFilters: {
      memory_budget: true,
      memory_compaction: true,
      memory_cache_hit: true,
      memory_cache_miss: true,
    },
    traceRenderMode: "plain",
    tracePhaseMode: "current",
    traceLaneMode: "my",
    toolsFilterText: "",
    selectedTrace: null,
    selectedElementId: null,
    selectedElement: null,
    selectedPage: null,
    themeSetting: "system",
    runtimeTheme: null,
    themeOverride: null,
    seedActionId: null,
    preferencePolicy: { allow_override: false, persist: "none" },
  };

  Object.keys(defaults).forEach((key) => {
    if (global[key] === undefined) {
      global[key] = defaults[key];
    }
  });

  let traceFilterTimer = null;
  let toolsFilterTimer = null;
  let versionLabel = null;

  function getCachedSummary() {
    return global.cachedSummary;
  }
  function setCachedSummary(value) {
    global.cachedSummary = value || {};
    return global.cachedSummary;
  }
  function getCachedState() {
    return global.cachedState;
  }
  function setCachedState(value) {
    global.cachedState = value || {};
    return global.cachedState;
  }
  function getCachedActions() {
    return global.cachedActions;
  }
  function setCachedActions(value) {
    global.cachedActions = value || {};
    return global.cachedActions;
  }
  function getCachedTraces() {
    return global.cachedTraces;
  }
  function setCachedTraces(value) {
    global.cachedTraces = Array.isArray(value) ? value : global.cachedTraces;
    return global.cachedTraces;
  }
  function getCachedAgreements() {
    return global.cachedAgreements;
  }
  function setCachedAgreements(value) {
    global.cachedAgreements = value;
    return global.cachedAgreements;
  }
  function getCachedRules() {
    return global.cachedRules;
  }
  function setCachedRules(value) {
    global.cachedRules = value;
    return global.cachedRules;
  }
  function getCachedHandoffs() {
    return global.cachedHandoffs;
  }
  function setCachedHandoffs(value) {
    global.cachedHandoffs = value;
    return global.cachedHandoffs;
  }
  function getCachedLint() {
    return global.cachedLint;
  }
  function setCachedLint(value) {
    global.cachedLint = value || {};
    return global.cachedLint;
  }
  function getCachedTools() {
    return global.cachedTools;
  }
  function setCachedTools(value) {
    global.cachedTools = value || {};
    return global.cachedTools;
  }
  function getCachedPacks() {
    return global.cachedPacks;
  }
  function setCachedPacks(value) {
    global.cachedPacks = value || {};
    return global.cachedPacks;
  }
  function getCachedSecurity() {
    return global.cachedSecurity;
  }
  function setCachedSecurity(value) {
    global.cachedSecurity = value || {};
    return global.cachedSecurity;
  }
  function getCachedManifest() {
    return global.cachedManifest;
  }
  function setCachedManifest(value) {
    global.cachedManifest = value;
    return global.cachedManifest;
  }
  function getTraceFilterText() {
    return global.traceFilterText;
  }
  function setTraceFilterText(value) {
    global.traceFilterText = value;
    return global.traceFilterText;
  }
  function getMemoryBudgetFilters() {
    return global.memoryBudgetFilters;
  }
  function setMemoryBudgetFilters(value) {
    global.memoryBudgetFilters = value || defaults.memoryBudgetFilters;
    return global.memoryBudgetFilters;
  }
  function setMemoryBudgetFilter(type, enabled) {
    const next = { ...getMemoryBudgetFilters(), [type]: enabled };
    return setMemoryBudgetFilters(next);
  }
  function getTraceFilterTimer() {
    return traceFilterTimer;
  }
  function setTraceFilterTimer(value) {
    traceFilterTimer = value;
    return traceFilterTimer;
  }
  function getTraceRenderMode() {
    return global.traceRenderMode;
  }
  function setTraceRenderMode(value) {
    global.traceRenderMode = value;
    return global.traceRenderMode;
  }
  function getTracePhaseMode() {
    return global.tracePhaseMode;
  }
  function setTracePhaseMode(value) {
    global.tracePhaseMode = value;
    return global.tracePhaseMode;
  }
  function getTraceLaneMode() {
    return global.traceLaneMode;
  }
  function setTraceLaneMode(value) {
    global.traceLaneMode = value;
    return global.traceLaneMode;
  }
  function getToolsFilterText() {
    return global.toolsFilterText;
  }
  function setToolsFilterText(value) {
    global.toolsFilterText = value;
    return global.toolsFilterText;
  }
  function getToolsFilterTimer() {
    return toolsFilterTimer;
  }
  function setToolsFilterTimer(value) {
    toolsFilterTimer = value;
    return toolsFilterTimer;
  }
  function getSelectedTrace() {
    return global.selectedTrace;
  }
  function setSelectedTrace(value) {
    global.selectedTrace = value;
    return global.selectedTrace;
  }
  function getSelectedElementId() {
    return global.selectedElementId;
  }
  function setSelectedElementId(value) {
    global.selectedElementId = value;
    return global.selectedElementId;
  }
  function getSelectedElement() {
    return global.selectedElement;
  }
  function setSelectedElement(value) {
    global.selectedElement = value;
    return global.selectedElement;
  }
  function getSelectedPage() {
    return global.selectedPage;
  }
  function setSelectedPage(value) {
    global.selectedPage = value;
    return global.selectedPage;
  }
  function getVersionLabelElement() {
    return versionLabel;
  }
  function setVersionLabelElement(value) {
    versionLabel = value;
    return versionLabel;
  }
  function getThemeSetting() {
    return global.themeSetting;
  }
  function setThemeSetting(value) {
    global.themeSetting = value;
    return global.themeSetting;
  }
  function getRuntimeTheme() {
    return global.runtimeTheme;
  }
  function setRuntimeTheme(value) {
    global.runtimeTheme = value;
    return global.runtimeTheme;
  }
  function getThemeOverride() {
    return global.themeOverride;
  }
  function setThemeOverride(value) {
    global.themeOverride = value;
    return global.themeOverride;
  }
  function getSeedActionId() {
    return global.seedActionId;
  }
  function setSeedActionId(value) {
    global.seedActionId = value;
    return global.seedActionId;
  }
  function getPreferencePolicy() {
    return global.preferencePolicy;
  }
  function setPreferencePolicy(value) {
    global.preferencePolicy = value || defaults.preferencePolicy;
    return global.preferencePolicy;
  }
  function getPersistenceInfo() {
    const manifest = global.cachedManifest;
    const persistence = (manifest && manifest.ui && manifest.ui.persistence) || {};
    const kind = (persistence.kind || "memory").toLowerCase();
    return {
      enabled: !!persistence.enabled,
      kind,
      path: persistence.path || "",
    };
  }

  state.getCachedSummary = getCachedSummary;
  state.setCachedSummary = setCachedSummary;
  state.getCachedState = getCachedState;
  state.setCachedState = setCachedState;
  state.getCachedActions = getCachedActions;
  state.setCachedActions = setCachedActions;
  state.getCachedTraces = getCachedTraces;
  state.setCachedTraces = setCachedTraces;
  state.getCachedAgreements = getCachedAgreements;
  state.setCachedAgreements = setCachedAgreements;
  state.getCachedRules = getCachedRules;
  state.setCachedRules = setCachedRules;
  state.getCachedHandoffs = getCachedHandoffs;
  state.setCachedHandoffs = setCachedHandoffs;
  state.getCachedLint = getCachedLint;
  state.setCachedLint = setCachedLint;
  state.getCachedTools = getCachedTools;
  state.setCachedTools = setCachedTools;
  state.getCachedPacks = getCachedPacks;
  state.setCachedPacks = setCachedPacks;
  state.getCachedSecurity = getCachedSecurity;
  state.setCachedSecurity = setCachedSecurity;
  state.getCachedManifest = getCachedManifest;
  state.setCachedManifest = setCachedManifest;
  state.getTraceFilterText = getTraceFilterText;
  state.setTraceFilterText = setTraceFilterText;
  state.getMemoryBudgetFilters = getMemoryBudgetFilters;
  state.setMemoryBudgetFilters = setMemoryBudgetFilters;
  state.setMemoryBudgetFilter = setMemoryBudgetFilter;
  state.getTraceFilterTimer = getTraceFilterTimer;
  state.setTraceFilterTimer = setTraceFilterTimer;
  state.getTraceRenderMode = getTraceRenderMode;
  state.setTraceRenderMode = setTraceRenderMode;
  state.getTracePhaseMode = getTracePhaseMode;
  state.setTracePhaseMode = setTracePhaseMode;
  state.getTraceLaneMode = getTraceLaneMode;
  state.setTraceLaneMode = setTraceLaneMode;
  state.getToolsFilterText = getToolsFilterText;
  state.setToolsFilterText = setToolsFilterText;
  state.getToolsFilterTimer = getToolsFilterTimer;
  state.setToolsFilterTimer = setToolsFilterTimer;
  state.getSelectedTrace = getSelectedTrace;
  state.setSelectedTrace = setSelectedTrace;
  state.getSelectedElementId = getSelectedElementId;
  state.setSelectedElementId = setSelectedElementId;
  state.getSelectedElement = getSelectedElement;
  state.setSelectedElement = setSelectedElement;
  state.getSelectedPage = getSelectedPage;
  state.setSelectedPage = setSelectedPage;
  state.getVersionLabelElement = getVersionLabelElement;
  state.setVersionLabelElement = setVersionLabelElement;
  state.getThemeSetting = getThemeSetting;
  state.setThemeSetting = setThemeSetting;
  state.getRuntimeTheme = getRuntimeTheme;
  state.setRuntimeTheme = setRuntimeTheme;
  state.getThemeOverride = getThemeOverride;
  state.setThemeOverride = setThemeOverride;
  state.getSeedActionId = getSeedActionId;
  state.setSeedActionId = setSeedActionId;
  state.getPreferencePolicy = getPreferencePolicy;
  state.setPreferencePolicy = setPreferencePolicy;
  state.getPersistenceInfo = getPersistenceInfo;
})();
