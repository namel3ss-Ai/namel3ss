(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const dom = root.dom;
  const net = root.net;
  const refresh = root.refresh || (root.refresh = {});

  function applyThemeFromManifest(manifest) {
    const theme = (manifest && manifest.theme) || {};
    const setting = theme.current || theme.setting || "system";
    state.setThemeSetting(theme.setting || setting);
    state.setRuntimeTheme(setting);
    if (typeof applyTheme === "function") {
      applyTheme(setting);
    }
    if (typeof applyThemeTokens === "function") {
      applyThemeTokens(theme.tokens || {}, setting);
    }
  }

  function applyManifest(manifest) {
    if (!manifest) return;
    state.setCachedManifest(manifest);
    if (typeof window.renderUI === "function") {
      window.renderUI(manifest);
    }
    applyThemeFromManifest(manifest);
    if (root.run && root.run.updateSeedAction) {
      root.run.updateSeedAction(manifest);
    }
  }

  async function refreshUI() {
    const container = document.getElementById("ui");
    try {
      const payload = await net.fetchJson("/api/ui");
      if (payload && payload.ok === false) {
        if (typeof window.renderUIError === "function") {
          window.renderUIError(payload.error || "Unable to load UI");
        } else {
          dom.showError(container, payload.error || "Unable to load UI");
        }
        return;
      }
      applyManifest(payload);
    } catch (err) {
      const detail = err && err.message ? err.message : "Unable to load UI";
      dom.showError(container, detail);
    }
  }

  refresh.applyManifest = applyManifest;
  refresh.refreshUI = refreshUI;
})();
