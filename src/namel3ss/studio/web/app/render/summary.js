(() => {
  const root = window.N3App || (window.N3App = {});
  const render = root.render || (root.render = {});
  const utils = root.utils;
  const state = root.state;

  function renderSummary(data) {
    state.setCachedSummary(data || {});
    const container = document.getElementById("summary");
    if (!container) return;
    container.innerHTML = "";
    if (!data || data.ok === false) {
      utils.showEmpty(container, data && data.error ? data.error : "Unable to load summary");
      utils.updateCopyButton("summaryCopy", () => "");
      return;
    }
    utils.setFileName(data.file);
    const counts = data.counts || {};
    const kv = document.createElement("div");
    kv.className = "key-values";
    Object.keys(counts).forEach((key) => {
      const row = document.createElement("div");
      row.className = "kv-row";
      row.innerHTML = `<div class=\"kv-label\">${key}</div><div class=\"kv-value\">${counts[key]}</div>`;
      kv.appendChild(row);
    });
    const manifest = state.getCachedManifest();
    if (manifest && manifest.theme) {
      const setting = manifest.theme.setting || "system";
      const runtime = manifest.theme.current || setting;
      const display = state.getThemeOverride() || runtime;
      const effective = resolveTheme(display);
      const tokenMap = applyThemeTokens(manifest.theme.tokens || {}, display);
      const row = document.createElement("div");
      row.className = "kv-row";
      const overrideLabel = state.getThemeOverride() ? " (preview override)" : "";
      row.innerHTML = `<div class=\"kv-label\">theme</div><div class=\"kv-value\">setting: ${setting}, engine: ${runtime}, effective: ${effective}${overrideLabel}</div>`;
      kv.appendChild(row);
      const tokensRow = document.createElement("div");
      tokensRow.className = "kv-row";
      tokensRow.innerHTML = `<div class=\"kv-label\">tokens</div><div class=\"kv-value\">${JSON.stringify(tokenMap)}</div>`;
      kv.appendChild(tokensRow);
      const pref = manifest.theme.preference || {};
      const prefRow = document.createElement("div");
      prefRow.className = "kv-row";
      prefRow.innerHTML = `<div class=\"kv-label\">preference</div><div class=\"kv-value\">allow_override: ${pref.allow_override ? "true" : "false"}, persist: ${pref.persist || "none"}</div>`;
      kv.appendChild(prefRow);
    }
    container.appendChild(kv);
    utils.updateCopyButton("summaryCopy", () => JSON.stringify(data, null, 2));
  }

  render.renderSummary = renderSummary;
  window.renderSummary = renderSummary;
})();
