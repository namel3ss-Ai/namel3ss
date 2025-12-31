(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state || (root.state = {});

  let cachedManifest = null;
  let cachedTraces = [];
  let seedActionId = null;
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
  function getCachedTraces() {
    return cachedTraces;
  }
  function setCachedTraces(value) {
    cachedTraces = Array.isArray(value) ? value : cachedTraces;
    return cachedTraces;
  }
  function getSeedActionId() {
    return seedActionId;
  }
  function setSeedActionId(value) {
    seedActionId = value || null;
    return seedActionId;
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
  state.getCachedTraces = getCachedTraces;
  state.setCachedTraces = setCachedTraces;
  state.getSeedActionId = getSeedActionId;
  state.setSeedActionId = setSeedActionId;
  state.getThemeSetting = getThemeSetting;
  state.setThemeSetting = setThemeSetting;
  state.getRuntimeTheme = getRuntimeTheme;
  state.setRuntimeTheme = setRuntimeTheme;
})();
