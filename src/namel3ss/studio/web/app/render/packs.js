(() => {
  const root = window.N3App || (window.N3App = {});
  const render = root.render || (root.render = {});
  const utils = root.utils;
  const state = root.state;

  function renderPacks(data) {
    state.setCachedPacks(data || {});
    const container = document.getElementById("packs");
    if (!container) return;
    container.innerHTML = "";
    if (!data || data.ok === false) {
      utils.showEmpty(container, data && data.error ? data.error : "Unable to load packs");
      utils.updateCopyButton("packsCopy", () => "");
      return;
    }
    const packs = data.packs || [];
    if (!packs.length) {
      utils.showEmpty(container, "No packs installed.");
      utils.updateCopyButton("packsCopy", () => JSON.stringify(data, null, 2));
      return;
    }
    const list = document.createElement("div");
    list.className = "list";
    packs.sort((a, b) => (a.pack_id || "").localeCompare(b.pack_id || "")).forEach((pack) => {
      const item = document.createElement("div");
      item.className = "list-item";
      const title = document.createElement("div");
      title.className = "list-title";
      title.textContent = `${pack.pack_id || "pack"} (${pack.version || "?"})`;
      const meta = document.createElement("div");
      meta.className = "list-meta";
      const status = pack.enabled ? "enabled" : "disabled";
      const verify = pack.verified ? "verified" : "unverified";
      meta.textContent = `${status} \u00b7 ${verify} \u00b7 ${pack.source || "installed"}`;
      item.appendChild(title);
      item.appendChild(meta);
      const actions = document.createElement("div");
      actions.className = "control-actions";
      if (!pack.verified) {
        const btn = document.createElement("button");
        btn.className = "btn ghost small";
        btn.textContent = "Verify";
        btn.onclick = () => render.packAction("/api/packs/verify", pack.pack_id);
        actions.appendChild(btn);
      }
      if (pack.verified && !pack.enabled) {
        const btn = document.createElement("button");
        btn.className = "btn ghost small";
        btn.textContent = "Enable";
        btn.onclick = () => render.packAction("/api/packs/enable", pack.pack_id);
        actions.appendChild(btn);
      }
      if (pack.enabled) {
        const btn = document.createElement("button");
        btn.className = "btn ghost small";
        btn.textContent = "Disable";
        btn.onclick = () => render.packAction("/api/packs/disable", pack.pack_id);
        actions.appendChild(btn);
      }
      item.appendChild(actions);
      list.appendChild(item);
    });
    container.appendChild(list);
    utils.updateCopyButton("packsCopy", () => JSON.stringify(data, null, 2));
  }

  render.renderPacks = renderPacks;
  window.renderPacks = renderPacks;
})();
