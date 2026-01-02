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
    updateAppNameFromManifest(manifest);
    if (root.preview && root.preview.applyManifest) {
      root.preview.applyManifest(manifest);
    }
    if (typeof window.renderData === "function") {
      window.renderData(manifest);
    }
    applyThemeFromManifest(manifest);
    if (root.run && root.run.updateSeedAction) {
      root.run.updateSeedAction(manifest);
    }
    if (root.run && root.run.updateResetAction) {
      root.run.updateResetAction(manifest);
    }
    if (root.menu && root.menu.updateMenuState) {
      root.menu.updateMenuState();
    }
  }

  function updateAppNameFromManifest(manifest) {
    const label = document.getElementById("appName");
    if (!label || !manifest || !manifest.pages) return;
    for (const page of manifest.pages) {
      const queue = Array.isArray(page.elements) ? [...page.elements] : [];
      while (queue.length) {
        const element = queue.shift();
        if (!element) continue;
        if (element.type === "title" && element.value) {
          label.textContent = element.value;
          return;
        }
        if (Array.isArray(element.children)) {
          queue.push(...element.children);
        }
      }
    }
  }

  function setManifestError(detail) {
    if (state && typeof state.setCachedLastRunError === "function") {
      state.setCachedLastRunError({ ok: false, error: detail, kind: "manifest" });
    }
    if (root.errors && typeof root.errors.renderErrors === "function") {
      root.errors.renderErrors();
    }
  }

  function clearManifestErrorIfPresent() {
    if (!state || typeof state.getCachedLastRunError !== "function") return;
    const current = state.getCachedLastRunError();
    if (!current || current.kind !== "manifest") return;
    if (typeof state.setCachedLastRunError === "function") {
      state.setCachedLastRunError(null);
    }
    if (root.errors && typeof root.errors.renderErrors === "function") {
      root.errors.renderErrors();
    }
  }

  async function refreshUI() {
    const container = document.getElementById("previewShell");
    try {
      const payload = await net.fetchJson("/api/ui");
      if (payload && payload.ok === false) {
        setManifestError(payload.error || "Unable to load UI");
        if (root.preview && root.preview.renderError) {
          root.preview.renderError(payload.error || "Unable to load UI");
        } else {
          dom.showError(container, payload.error || "Unable to load UI");
        }
        return;
      }
      clearManifestErrorIfPresent();
      applyManifest(payload);
      if (root.setup && root.setup.refreshSetup) {
        root.setup.refreshSetup();
      }
    } catch (err) {
      const detail = err && err.message ? err.message : "Unable to load UI";
      setManifestError(detail);
      if (root.preview && root.preview.renderError) {
        root.preview.renderError(detail);
      } else {
        dom.showError(container, detail);
      }
    }
  }

  async function refreshSummary() {
    const label = document.getElementById("appName");
    try {
      const payload = await net.fetchJson("/api/summary");
      if (state && typeof state.setCachedSummary === "function") {
        state.setCachedSummary(payload);
      }
      if (label && (!label.textContent || label.textContent === "App")) {
        const file = payload && payload.file ? String(payload.file) : "";
        const parts = file.split(/[/\\\\]/).filter(Boolean);
        let name = parts.length > 1 ? parts[parts.length - 2] : parts[parts.length - 1];
        if (!name) name = "App";
        label.textContent = name;
      }
      if (root.setup && typeof root.setup.updateAiBadge === "function") {
        root.setup.updateAiBadge(payload);
      }
    } catch (err) {
      if (label && (!label.textContent || label.textContent === "App")) {
        label.textContent = "App";
      }
    }
  }

  async function refreshDiagnostics() {
    try {
      const payload = await net.fetchJson("/api/diagnostics");
      if (state && typeof state.setCachedDiagnostics === "function") {
        state.setCachedDiagnostics(payload);
      }
      if (root.errors && typeof root.errors.renderErrors === "function") {
        root.errors.renderErrors();
      }
    } catch (_err) {
      if (state && typeof state.setCachedDiagnostics === "function") {
        state.setCachedDiagnostics(null);
      }
    }
  }

  refresh.applyManifest = applyManifest;
  refresh.refreshUI = refreshUI;
  refresh.refreshSummary = refreshSummary;
  refresh.refreshDiagnostics = refreshDiagnostics;
})();
