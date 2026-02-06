(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const net = root.net;
  const secretsApi = root.secrets || {};
  const providerSetup = root.providerSetup || (root.providerSetup = {});

  let cachedPayload = null;

  function normalizeRows(payload) {
    if (!payload || payload.ok === false || !Array.isArray(payload.providers)) return [];
    const rows = payload.providers
      .filter((row) => row && row.name)
      .map((row) => ({
        name: String(row.name || "").trim().toLowerCase(),
        capabilityToken: String(row.capability_token || "").trim(),
        supportedModes: Array.isArray(row.supported_modes) ? row.supported_modes.map((item) => String(item)) : [],
        models: Array.isArray(row.models) ? row.models.map((item) => String(item)) : [],
        installed: row.installed !== false,
        usedInApp: row.used_in_app === true,
        defaultModel: String(row.default_model || "").trim(),
        secretName: String(row.secret_name || "").trim(),
      }))
      .sort((left, right) => left.name.localeCompare(right.name));
    return rows;
  }

  function providerLabel(name) {
    const token = String(name || "").trim();
    if (!token) return "Provider";
    return token
      .split("_")
      .map((piece) => piece.charAt(0).toUpperCase() + piece.slice(1))
      .join(" ");
  }

  function modeText(row) {
    if (!row.supportedModes.length) return "text";
    return row.supportedModes.join(", ");
  }

  function buildProvidersTable(rows) {
    const table = document.createElement("table");
    table.className = "ui-table setup-table providers-table";
    const head = document.createElement("thead");
    const headerRow = document.createElement("tr");
    ["Provider", "Capability", "Modes", "Installed", "Used in app"].forEach((title) => {
      const th = document.createElement("th");
      th.textContent = title;
      headerRow.appendChild(th);
    });
    head.appendChild(headerRow);
    table.appendChild(head);

    const body = document.createElement("tbody");
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      const provider = document.createElement("td");
      provider.textContent = providerLabel(row.name);
      const capability = document.createElement("td");
      capability.textContent = row.capabilityToken || "n/a";
      const modes = document.createElement("td");
      modes.textContent = modeText(row);
      const installed = document.createElement("td");
      installed.textContent = row.installed ? "yes" : "no";
      const used = document.createElement("td");
      used.textContent = row.usedInApp ? "yes" : "no";
      tr.appendChild(provider);
      tr.appendChild(capability);
      tr.appendChild(modes);
      tr.appendChild(installed);
      tr.appendChild(used);
      body.appendChild(tr);
    });
    table.appendChild(body);
    return table;
  }

  function providerSecretHint(providerName) {
    if (typeof secretsApi.listProviderKeys !== "function") return "";
    const keys = secretsApi.listProviderKeys(providerName);
    if (!keys.length) return "";
    return keys.join(", ");
  }

  function buildSettingsForm(rows) {
    const wrapper = document.createElement("div");
    wrapper.className = "provider-settings";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Provider defaults";
    wrapper.appendChild(title);

    const helper = document.createElement("div");
    helper.className = "provider-settings-help";
    helper.textContent = "Set default model IDs and secret names used for provider calls.";
    wrapper.appendChild(helper);

    const controls = {};
    rows.forEach((row) => {
      const card = document.createElement("div");
      card.className = "provider-settings-card";

      const name = document.createElement("div");
      name.className = "provider-settings-name";
      name.textContent = providerLabel(row.name);
      card.appendChild(name);

      const modelLabel = document.createElement("label");
      modelLabel.textContent = "Default model";
      const modelSelect = document.createElement("select");
      modelSelect.className = "provider-settings-select";
      row.models.forEach((modelId) => {
        const option = document.createElement("option");
        option.value = modelId;
        option.textContent = modelId;
        if (modelId === row.defaultModel) option.selected = true;
        modelSelect.appendChild(option);
      });
      if (!row.models.length) {
        modelSelect.disabled = true;
      }
      modelLabel.appendChild(modelSelect);
      card.appendChild(modelLabel);

      const secretLabel = document.createElement("label");
      secretLabel.textContent = "Secret name";
      const secretInput = document.createElement("input");
      secretInput.type = "text";
      secretInput.className = "provider-settings-input";
      secretInput.value = row.secretName;
      const secretHint = providerSecretHint(row.name);
      secretInput.placeholder = secretHint || "optional";
      if (!secretHint) {
        secretInput.disabled = true;
      }
      secretLabel.appendChild(secretInput);
      card.appendChild(secretLabel);

      controls[row.name] = { modelSelect, secretInput };
      wrapper.appendChild(card);
    });

    const actions = document.createElement("div");
    actions.className = "provider-settings-actions";
    const saveButton = document.createElement("button");
    saveButton.type = "button";
    saveButton.className = "btn ghost";
    saveButton.textContent = "Save provider settings";
    const status = document.createElement("div");
    status.className = "provider-settings-status";
    actions.appendChild(saveButton);
    actions.appendChild(status);
    wrapper.appendChild(actions);

    saveButton.onclick = async () => {
      status.textContent = "Saving...";
      saveButton.disabled = true;
      try {
        const settings = {};
        Object.keys(controls)
          .sort()
          .forEach((providerName) => {
            const modelSelect = controls[providerName].modelSelect;
            const secretInput = controls[providerName].secretInput;
            settings[providerName] = {
              default_model: modelSelect && !modelSelect.disabled ? String(modelSelect.value || "").trim() : "",
              secret_name: secretInput && !secretInput.disabled ? String(secretInput.value || "").trim() : "",
            };
          });
        const payload = await net.postJson("/api/providers", {
          action: "save",
          settings: settings,
        });
        cachedPayload = payload;
        if (payload && payload.ok === false) {
          status.textContent = payload.error || "Unable to save provider settings.";
        } else {
          status.textContent = "Saved.";
        }
      } catch (err) {
        status.textContent = err && err.message ? err.message : "Unable to save provider settings.";
      } finally {
        saveButton.disabled = false;
      }
    };
    return wrapper;
  }

  function renderProviders(container, payload) {
    if (!container) return;
    const section = document.createElement("div");
    section.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Provider packs";
    section.appendChild(title);
    container.appendChild(section);

    if (!payload || payload.ok === false) {
      const warning = document.createElement("div");
      warning.className = "status-banner warning";
      warning.textContent = payload && payload.error ? payload.error : "Provider metadata is unavailable.";
      container.appendChild(warning);
      return;
    }

    const rows = normalizeRows(payload);
    if (!rows.length) {
      const empty = document.createElement("div");
      empty.className = "status-banner";
      empty.textContent = "No provider packs were found.";
      container.appendChild(empty);
      return;
    }
    container.appendChild(buildProvidersTable(rows));
    container.appendChild(buildSettingsForm(rows));
  }

  async function refreshProviders() {
    const payload = await net.fetchJson("/api/providers");
    cachedPayload = payload;
    return payload;
  }

  function getCachedProviders() {
    return cachedPayload;
  }

  providerSetup.renderProviders = renderProviders;
  providerSetup.refreshProviders = refreshProviders;
  providerSetup.getCachedProviders = getCachedProviders;
})();
