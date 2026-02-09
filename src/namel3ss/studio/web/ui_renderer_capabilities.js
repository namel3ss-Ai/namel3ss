(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});

  function renderCapabilitiesElement(el) {
    const wrapper = document.createElement("section");
    wrapper.className = "ui-element ui-capabilities";

    const heading = document.createElement("h3");
    heading.className = "ui-capabilities-heading";
    heading.textContent = "Capability Packs";
    wrapper.appendChild(heading);

    const versions = normalizeVersions(el && el.capability_versions);
    const packs = normalizePacks(el && el.capabilities_enabled, versions);
    if (!packs.length) {
      const empty = document.createElement("div");
      empty.className = "ui-capabilities-empty";
      empty.textContent = "No capability packs enabled.";
      wrapper.appendChild(empty);
      return wrapper;
    }

    const list = document.createElement("div");
    list.className = "ui-capabilities-list";
    packs.forEach((pack) => {
      const item = document.createElement("article");
      item.className = "ui-capabilities-item";

      const header = document.createElement("div");
      header.className = "ui-capabilities-item-header";
      const name = document.createElement("span");
      name.className = "ui-capabilities-name";
      name.textContent = pack.name;
      const version = document.createElement("span");
      version.className = "ui-capabilities-version";
      version.textContent = pack.version;
      header.appendChild(name);
      header.appendChild(version);
      item.appendChild(header);

      item.appendChild(metaRow("Purity", pack.purity || "effectful"));
      item.appendChild(metaRow("Replay", pack.replay_mode || "verify"));
      item.appendChild(metaRow("Permissions", pack.required_permissions.join(", ") || "none"));
      item.appendChild(metaRow("Effects", pack.effect_capabilities.join(", ") || "none"));
      item.appendChild(metaRow("Actions", pack.provided_actions.join(", ") || "none"));

      list.appendChild(item);
    });
    wrapper.appendChild(list);
    return wrapper;
  }

  function normalizePacks(value, versions) {
    if (!Array.isArray(value)) return [];
    const packs = [];
    const seen = new Set();
    value.forEach((entry) => {
      if (!entry || typeof entry !== "object") return;
      const name = text(entry.name).toLowerCase();
      if (!name || seen.has(name)) return;
      seen.add(name);
      packs.push({
        name: name,
        version: text(entry.version) || versions[name] || "unknown",
        provided_actions: textList(entry.provided_actions),
        required_permissions: textList(entry.required_permissions),
        effect_capabilities: textList(entry.effect_capabilities),
        purity: text(entry.purity),
        replay_mode: text(entry.replay_mode),
      });
    });
    packs.sort((a, b) => a.name.localeCompare(b.name) || a.version.localeCompare(b.version));
    return packs;
  }

  function normalizeVersions(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return {};
    const versions = {};
    Object.keys(value)
      .sort()
      .forEach((key) => {
        const name = text(key).toLowerCase();
        const version = text(value[key]);
        if (!name || !version) return;
        versions[name] = version;
      });
    return versions;
  }

  function textList(value) {
    if (!Array.isArray(value)) return [];
    const deduped = new Set();
    value.forEach((item) => {
      const token = text(item).toLowerCase();
      if (token) deduped.add(token);
    });
    return Array.from(deduped).sort();
  }

  function text(value) {
    if (typeof value !== "string") return "";
    return value.trim();
  }

  function metaRow(label, value) {
    const row = document.createElement("div");
    row.className = "ui-capabilities-row";
    const key = document.createElement("span");
    key.className = "ui-capabilities-label";
    key.textContent = `${label}:`;
    const textNode = document.createElement("span");
    textNode.className = "ui-capabilities-value";
    textNode.textContent = value;
    row.appendChild(key);
    row.appendChild(textNode);
    return row;
  }

  root.renderCapabilitiesElement = renderCapabilitiesElement;
})();
