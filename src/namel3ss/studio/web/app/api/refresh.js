(() => {
  const root = window.N3App || (window.N3App = {});
  const api = root.api || (root.api = {});
  const state = root.state;
  const utils = root.utils;
  const constants = root.constants;

  function detectSeedAction(manifest, actionsPayload) {
    const preferred = constants.PREFERRED_SEED_ACTIONS;
    const actions = actionsPayload?.actions || Object.values(manifest?.actions || {});
    const callFlows = actions.filter((a) => a.type === "call_flow");
    for (const name of preferred) {
      const found = callFlows.find((a) => a.flow === name);
      if (found) return found.id || found.action_id || `action.${name}`;
    }
    return callFlows.length ? callFlows[0].id || callFlows[0].action_id || null : null;
  }

  function toggleSeed(actionId) {
    const btn = document.getElementById("seed");
    if (!btn) return;
    if (actionId) btn.classList.remove("hidden");
    else btn.classList.add("hidden");
  }

  async function refreshAll() {
    const [summary, ui, actions, lint, tools, packs, security] = await Promise.all([
      utils.fetchJson("/api/summary"),
      utils.fetchJson("/api/ui"),
      utils.fetchJson("/api/actions"),
      utils.fetchJson("/api/lint"),
      utils.fetchJson("/api/tools"),
      utils.fetchJson("/api/packs"),
      utils.fetchJson("/api/security"),
    ]);
    if (window.renderSummary) window.renderSummary(summary);
    if (window.renderActions) window.renderActions(actions);
    if (window.renderLint) window.renderLint(lint);
    if (window.renderTools) window.renderTools(tools);
    if (window.renderPacks) window.renderPacks(packs);
    if (window.renderSecurity) window.renderSecurity(security);
    if (window.renderState) window.renderState({});
    if (window.renderTraces) window.renderTraces([]);
    if (ui.ok !== false) {
      state.setCachedManifest(ui);
      if (window.renderUI) window.renderUI(ui);
    } else {
      const uiContainer = document.getElementById("ui");
      utils.showEmpty(uiContainer, ui.error || "Unable to load UI");
    }
    const manifest = state.getCachedManifest();
    const setting = (manifest && manifest.theme && manifest.theme.setting) || "system";
    const runtime = (manifest && manifest.theme && manifest.theme.current) || setting;
    state.setThemeSetting(setting);
    state.setRuntimeTheme(runtime);
    state.setPreferencePolicy((manifest && manifest.theme && manifest.theme.preference) || state.getPreferencePolicy());
    const currentTheme = state.getThemeOverride() || runtime;
    applyTheme(currentTheme);
    const activeTokens = (manifest && manifest.theme && manifest.theme.tokens) || {};
    applyThemeTokens(activeTokens, currentTheme);
    const selector = document.getElementById("themeSelect");
    if (selector) {
      selector.value = state.getThemeOverride() || runtime || setting;
      selector.disabled = !state.getPreferencePolicy().allow_override;
    }
    const seedActionId = detectSeedAction(manifest, actions);
    state.setSeedActionId(seedActionId);
    toggleSeed(seedActionId);
    applyLocalPreferenceIfNeeded();
    renderTruthBar(manifest);
    if (window.reselectElement) window.reselectElement();
    if (window.refreshGraphPanel) window.refreshGraphPanel();
    if (window.refreshTrustPanel) window.refreshTrustPanel();
    if (window.refreshDataPanel) window.refreshDataPanel();
    if (window.refreshFixPanel) window.refreshFixPanel();
    if (window.refreshAgreements) window.refreshAgreements();
    if (window.refreshRules) window.refreshRules();
  }

  async function loadVersion() {
    try {
      const data = await utils.fetchJson("/api/version");
      if (data && data.ok && data.version) {
        utils.setVersionLabel(data.version);
      }
    } catch (err) {
      utils.setVersionLabel("");
    }
  }

  api.refreshAll = refreshAll;
  api.loadVersion = loadVersion;
  api.detectSeedAction = detectSeedAction;
  api.toggleSeed = toggleSeed;
  window.refreshAll = refreshAll;
})();
