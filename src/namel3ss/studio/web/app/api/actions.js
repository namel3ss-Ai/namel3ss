(() => {
  const root = window.N3App || (window.N3App = {});
  const api = root.api || (root.api = {});
  const state = root.state;
  const utils = root.utils;

  async function executeAction(actionId, payload) {
    const res = await fetch("/api/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: actionId, payload }),
    });
    const data = await res.json();
    if (!data.ok) {
      utils.showToast("Action failed safely.");
      if (data.error) utils.showToast(data.error);
    }
    if (!data.ok && data.errors) {
      return data;
    }
    if (data.state && window.renderState) {
      window.renderState(data.state);
    }
    if (data.traces && window.renderTraces) {
      window.renderTraces(data.traces);
      if (window.refreshAgreements) window.refreshAgreements();
    }
    if (data.ui) {
      state.setCachedManifest(data.ui);
      if (window.renderUI) window.renderUI(data.ui);
      const setting = (state.getCachedManifest().theme && state.getCachedManifest().theme.setting) || "system";
      const runtime = (state.getCachedManifest().theme && state.getCachedManifest().theme.current) || setting;
      state.setThemeSetting(setting);
      state.setRuntimeTheme(runtime);
      const currentTheme = state.getThemeOverride() || runtime;
      applyTheme(currentTheme);
      applyThemeTokens(
        state.getCachedManifest().theme && state.getCachedManifest().theme.tokens ? state.getCachedManifest().theme.tokens : {},
        currentTheme
      );
      const selector = document.getElementById("themeSelect");
      if (selector) selector.value = state.getThemeOverride() || setting;
    }
    if (window.reselectElement) window.reselectElement();
    return data;
  }

  api.executeAction = executeAction;
  window.executeAction = executeAction;
})();
