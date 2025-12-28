(() => {
  const root = window.N3App || (window.N3App = {});
  const setup = root.setup || (root.setup = {});
  const state = root.state;
  const utils = root.utils;

  function setupSeedButton() {
    const seedButton = document.getElementById("seed");
    if (!seedButton) return;
    seedButton.onclick = async () => {
      const seedActionId = state.getSeedActionId();
      if (!seedActionId) {
        utils.showToast("No seed action found.");
        return;
      }
      if (window.executeAction) await window.executeAction(seedActionId, {});
      if (window.refreshAll) window.refreshAll();
    };
  }

  function setupCoreButtons() {
    const refreshBtn = document.getElementById("refresh");
    if (refreshBtn) refreshBtn.onclick = window.refreshAll;

    const resetBtn = document.getElementById("reset");
    if (resetBtn) {
      resetBtn.onclick = async () => {
        const persistence = state.getPersistenceInfo();
        const resetPath = persistence.path ? ` in ${persistence.path}` : "";
        const prompt =
          persistence.kind === "sqlite" && persistence.enabled
            ? `Reset will clear persisted records/state${resetPath}. Continue?`
            : "Reset will clear state and records for this session. Continue?";
        const ok = window.confirm(prompt);
        if (!ok) return;
        await fetch("/api/reset", { method: "POST", body: "{}" });
        if (window.renderState) window.renderState({});
        if (window.renderTraces) window.renderTraces([]);
        if (window.refreshAll) window.refreshAll();
      };
    }

    const themeSelect = document.getElementById("themeSelect");
    if (themeSelect) {
      themeSelect.onchange = (e) => {
        const value = e.target.value;
        const preferencePolicy = state.getPreferencePolicy();
        const manifest = state.getCachedManifest();
        if (!preferencePolicy.allow_override) {
          state.setThemeOverride(value);
          applyTheme(value);
          const tokens = (manifest && manifest.theme && manifest.theme.tokens) || {};
          applyThemeTokens(tokens, value);
          renderTruthBar(manifest);
          if (window.renderSummary) window.renderSummary(state.getCachedSummary());
          if (manifest) {
            if (window.renderUI) window.renderUI(manifest);
            if (window.reselectElement) window.reselectElement();
          }
          return;
        }
        state.setThemeOverride(null);
        updateRuntimeTheme(value, preferencePolicy.persist);
      };
    }
  }

  function setupHelpModal() {
    const helpButton = document.getElementById("helpButton");
    const helpModal = document.getElementById("helpModal");
    const helpClose = document.getElementById("helpClose");
    if (helpButton && helpModal && helpClose) {
      helpButton.onclick = () => helpModal.classList.remove("hidden");
      helpClose.onclick = () => helpModal.classList.add("hidden");
      helpModal.addEventListener("click", (e) => {
        if (e.target === helpModal) {
          helpModal.classList.add("hidden");
        }
      });
    }
  }

  function setupToolsButtons() {
    const toolsAutoBind = document.getElementById("toolsAutoBind");
    if (toolsAutoBind) {
      toolsAutoBind.onclick = async () => {
        try {
          const resp = await fetch("/api/tools/auto-bind", { method: "POST", body: "{}" });
          const data = await resp.json();
          if (data.ok) {
            const count = (data.missing_bound || []).length;
            utils.showToast(count ? `Auto-bound ${count} tools.` : "No missing bindings.");
            if (window.refreshAll) window.refreshAll();
            return;
          }
          utils.showToast(data.error || "Auto-bind failed.");
        } catch (err) {
          utils.showToast("Auto-bind failed.");
        }
      };
    }
    const toolsOpenWizard = document.getElementById("toolsOpenWizard");
    if (toolsOpenWizard) {
      toolsOpenWizard.onclick = () => {
        const btn = document.getElementById("toolWizardButton");
        if (btn) btn.click();
      };
    }
    const toolsFixToggle = document.getElementById("toolsFixToggle");
    if (toolsFixToggle) {
      toolsFixToggle.onclick = () => {
        const panel = document.getElementById("toolsFixPanel");
        if (!panel) return;
        panel.classList.toggle("hidden");
      };
    }
  }

  function setupPacksButtons() {
    const packsRefresh = document.getElementById("packsRefresh");
    if (packsRefresh) {
      packsRefresh.onclick = () => window.refreshAll && window.refreshAll();
    }
    const securityRefresh = document.getElementById("securityRefresh");
    if (securityRefresh) {
      securityRefresh.onclick = () => window.refreshSecurity && window.refreshSecurity();
    }
    const packsAdd = document.getElementById("packsAdd");
    if (packsAdd) {
      packsAdd.onclick = async () => {
        const input = document.getElementById("packsPath");
        const path = input ? input.value.trim() : "";
        if (!path) {
          utils.showToast("Pack path required.");
          return;
        }
        try {
          const resp = await fetch("/api/packs/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path }),
          });
          const data = await resp.json();
          if (!data.ok) {
            utils.showToast(data.error || "Pack add failed.");
            return;
          }
          if (input) input.value = "";
          utils.showToast("Pack installed.");
          if (window.refreshAll) window.refreshAll();
        } catch (err) {
          utils.showToast("Pack add failed.");
        }
      };
    }
  }

  setup.setupSeedButton = setupSeedButton;
  setup.setupCoreButtons = setupCoreButtons;
  setup.setupHelpModal = setupHelpModal;
  setup.setupToolsButtons = setupToolsButtons;
  setup.setupPacksButtons = setupPacksButtons;
})();
