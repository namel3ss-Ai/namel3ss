(() => {
  const root = window.N3App || (window.N3App = {});
  const render = root.render || (root.render = {});
  const utils = root.utils;
  const state = root.state;
  const bracketRe = /[\\[\\]\\(\\)\\{\\}]/g;

  function appendSection(panel, title, lines, emptyText) {
    const label = document.createElement("div");
    label.className = "inline-label";
    label.textContent = title;
    panel.appendChild(label);
    if (!lines || !lines.length) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = emptyText || "No details.";
      panel.appendChild(empty);
      return;
    }
    panel.appendChild(utils.createCodeBlock(lines.join("\n")));
  }

  function packOrderLines(order) {
    if (!Array.isArray(order) || !order.length) return [];
    return order.map((packId, idx) => `Order ${idx + 1} is ${sanitize(packId)}.`);
  }

  function packDetailLines(packs) {
    if (!Array.isArray(packs) || !packs.length) return [];
    const lines = [];
    packs.forEach((pack) => {
      if (!pack) return;
      lines.push(`Pack id is ${sanitize(pack.pack_id)}.`);
      lines.push(`Pack name is ${sanitize(pack.pack_name)}.`);
      lines.push(`Pack version is ${sanitize(pack.pack_version)}.`);
      const provides = Array.isArray(pack.provides) ? pack.provides : [];
      if (provides.length) {
        const safeProvides = provides.map((entry) => sanitize(entry));
        lines.push(`Provides ${safeProvides.join(", ")}.`);
      } else {
        lines.push("Provides no settings.");
      }
      if (pack.rules_count !== undefined && pack.rules_count !== null) {
        lines.push(`Rules count is ${pack.rules_count}.`);
      }
    });
    return lines;
  }

  function ruleSourceLines(ruleSources) {
    if (!Array.isArray(ruleSources) || !ruleSources.length) return [];
    const lines = [];
    ruleSources.forEach((entry) => {
      if (!entry) return;
      const text = sanitize(entry.text || "Rule");
      const source = sanitize(entry.source || "default");
      lines.push(`Rule is ${text}. Source is ${source}.`);
    });
    return lines;
  }

  function sanitize(value) {
    const text = value === undefined || value === null ? "" : String(value);
    return text.replace(bracketRe, " ").replace(/\\s+/g, " ").trim();
  }

  function renderMemoryPacks(data) {
    const nextValue = data || state.getCachedMemoryPacks();
    state.setCachedMemoryPacks(nextValue);
    const panel = document.getElementById("memoryPacksPanel");
    if (!panel) return;
    panel.innerHTML = "";
    if (!nextValue || nextValue.ok === false) {
      const error = (nextValue && nextValue.error) || "Unable to load memory packs.";
      utils.showEmpty(panel, error);
      return;
    }
    appendSection(panel, "Active packs", nextValue.active_lines || [], "No packs found.");
    appendSection(panel, "Pack order", packOrderLines(nextValue.order || []), "No pack order.");
    appendSection(panel, "Overrides", nextValue.override_lines || [], "No overrides.");
    appendSection(panel, "Pack details", packDetailLines(nextValue.packs || []), "No pack details.");
    appendSection(panel, "Rule sources", ruleSourceLines(nextValue.rule_sources || []), "No rule sources.");
  }

  async function refreshMemoryPacks() {
    const data = await utils.fetchJson("/api/memory/packs");
    renderMemoryPacks(data);
  }

  render.renderMemoryPacks = renderMemoryPacks;
  render.refreshMemoryPacks = refreshMemoryPacks;
  window.renderMemoryPacks = renderMemoryPacks;
  window.refreshMemoryPacks = refreshMemoryPacks;
})();
