(() => {
  const root = window.N3App || (window.N3App = {});
  const render = root.render || (root.render = {});
  const utils = root.utils;
  const state = root.state;

  function _badge(label, kind) {
    const badge = document.createElement("span");
    badge.className = `badge ${kind || ""}`.trim();
    badge.textContent = label;
    return badge;
  }

  function _formatGuarantees(guarantees) {
    const fields = [
      "no_filesystem_write",
      "no_filesystem_read",
      "no_network",
      "no_subprocess",
      "no_env_read",
      "no_env_write",
    ];
    const parts = fields.map((field) => `${field}=${guarantees[field] ? "true" : "false"}`);
    if (Array.isArray(guarantees.secrets_allowed)) {
      parts.push(`secrets_allowed=[${guarantees.secrets_allowed.join(", ")}]`);
    }
    return parts.join(" \u00b7 ");
  }

  function _renderOverrides(toolName, overrides) {
    const wrapper = document.createElement("div");
    wrapper.className = "security-overrides";
    const heading = document.createElement("div");
    heading.className = "inline-label";
    heading.textContent = "Overrides (downgrade + unsafe)";
    wrapper.appendChild(heading);

    const grid = document.createElement("div");
    grid.className = "security-override-grid";
    const fields = [
      "no_filesystem_write",
      "no_filesystem_read",
      "no_network",
      "no_subprocess",
      "no_env_read",
      "no_env_write",
    ];
    const inputs = {};
    fields.forEach((field) => {
      const label = document.createElement("label");
      label.className = "security-override-field";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = overrides && overrides[field] === true;
      inputs[field] = input;
      label.appendChild(input);
      const span = document.createElement("span");
      span.textContent = field;
      label.appendChild(span);
      grid.appendChild(label);
    });
    wrapper.appendChild(grid);

    const secretsRow = document.createElement("label");
    secretsRow.className = "security-override-field wide";
    secretsRow.textContent = "secrets_allowed (comma separated)";
    const secretsInput = document.createElement("input");
    secretsInput.type = "text";
    secretsInput.value = Array.isArray(overrides.secrets_allowed) ? overrides.secrets_allowed.join(", ") : "";
    secretsRow.appendChild(secretsInput);
    wrapper.appendChild(secretsRow);

    const unsafeRow = document.createElement("label");
    unsafeRow.className = "security-override-field wide warning";
    const unsafeInput = document.createElement("input");
    unsafeInput.type = "checkbox";
    unsafeInput.checked = overrides && overrides.allow_unsafe_execution === true;
    unsafeRow.appendChild(unsafeInput);
    const unsafeLabel = document.createElement("span");
    unsafeLabel.textContent = "allow_unsafe_execution (bypass enforcement checks)";
    unsafeRow.appendChild(unsafeLabel);
    wrapper.appendChild(unsafeRow);

    const actions = document.createElement("div");
    actions.className = "control-actions";
    const applyBtn = document.createElement("button");
    applyBtn.className = "btn secondary small";
    applyBtn.textContent = "Apply overrides";
    applyBtn.onclick = async () => {
      if (!toolName) return;
      const warning = unsafeInput.checked ? "\nThis enables unsafe execution." : "";
      const ok = window.confirm(`Apply capability overrides for \"${toolName}\"?${warning}`);
      if (!ok) return;
      const nextOverrides = {};
      fields.forEach((field) => {
        if (inputs[field] && inputs[field].checked) {
          nextOverrides[field] = true;
        }
      });
      const secrets = secretsInput.value
        .split(",")
        .map((value) => value.trim())
        .filter((value) => value);
      if (secrets.length) {
        nextOverrides.secrets_allowed = secrets;
      }
      if (unsafeInput.checked) {
        nextOverrides.allow_unsafe_execution = true;
      }
      const okResp = await applySecurityOverride(toolName, nextOverrides);
      if (okResp) {
        refreshSecurity();
      }
    };
    actions.appendChild(applyBtn);
    wrapper.appendChild(actions);
    return wrapper;
  }

  async function applySecurityOverride(toolName, overrides) {
    try {
      const resp = await fetch("/api/security/override", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool_name: toolName, overrides: overrides || {} }),
      });
      const data = await resp.json();
      if (!data.ok) {
        utils.showToast(data.error || "Override update failed.");
        return false;
      }
      utils.showToast("Overrides updated.");
      return true;
    } catch (err) {
      utils.showToast("Override update failed.");
      return false;
    }
  }

  async function updateSandbox(toolName, enabled) {
    try {
      const resp = await fetch("/api/security/sandbox", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool_name: toolName, enabled: !!enabled }),
      });
      const data = await resp.json();
      if (!data.ok) {
        utils.showToast(data.error || "Sandbox update failed.");
        return;
      }
      utils.showToast(`Sandbox ${enabled ? "enabled" : "disabled"}.`);
      refreshSecurity();
    } catch (err) {
      utils.showToast("Sandbox update failed.");
    }
  }

  async function refreshSecurity() {
    try {
      const data = await utils.fetchJson("/api/security");
      renderSecurity(data);
    } catch (err) {
      renderSecurity({ ok: false, error: "Unable to load security lens" });
    }
  }

  function renderSecurity(data) {
    state.setCachedSecurity(data || {});
    const container = document.getElementById("security");
    if (!container) return;
    container.innerHTML = "";
    if (!data || data.ok === false) {
      utils.showEmpty(container, data && data.error ? data.error : "Unable to load security lens");
      utils.updateCopyButton("securityCopy", () => "");
      return;
    }
    const tools = data.tools || [];
    if (!tools.length) {
      utils.showEmpty(container, "No tools declared.");
      utils.updateCopyButton("securityCopy", () => JSON.stringify(data, null, 2));
      return;
    }
    const list = document.createElement("div");
    list.className = "list";
    tools.sort((a, b) => (a.tool_name || "").localeCompare(b.tool_name || "")).forEach((tool) => {
      const item = document.createElement("div");
      item.className = "list-item";
      const title = document.createElement("div");
      title.className = "list-title";
      title.textContent = tool.tool_name || "tool";
      const meta = document.createElement("div");
      meta.className = "list-meta";
      const source = tool.resolved_source || "unknown";
      const runner = tool.runner || "unknown";
      const coverage = tool.coverage || {};
      const coverageStatus = coverage.status || "unknown";
      const sandboxEnabled = !!(tool.sandbox && tool.sandbox.enabled);
      const metaParts = [`source: ${source}`, `runner: ${runner}`, `coverage: ${coverageStatus}`];
      if (runner === "local") {
        metaParts.push(`sandbox: ${sandboxEnabled ? "on" : "off"}`);
      }
      if (runner === "service" && coverage.service_handshake) {
        metaParts.push(`handshake: ${coverage.service_handshake}`);
      }
      if (runner === "container") {
        metaParts.push(`enforcement: ${coverage.container_enforcement || "missing"}`);
      }
      meta.textContent = metaParts.join(" \u00b7 ");
      const badges = document.createElement("div");
      badges.className = "badge-row";
      if (tool.blocked) {
        badges.appendChild(_badge("blocked", "bad"));
      } else {
        badges.appendChild(_badge("enforced", "ok"));
      }
      if (coverageStatus && coverageStatus !== "enforced") {
        badges.appendChild(_badge(`coverage ${coverageStatus}`, "warn"));
      }
      if (tool.unsafe_override) {
        badges.appendChild(_badge("unsafe override", "bad"));
      }
      item.appendChild(title);
      item.appendChild(meta);
      if (badges.childNodes.length) {
        item.appendChild(badges);
      }
      const guaranteesLine = document.createElement("div");
      guaranteesLine.className = "list-meta";
      guaranteesLine.textContent = `guarantees: ${_formatGuarantees(tool.guarantees || {})}`;
      item.appendChild(guaranteesLine);
      const sourcesLine = document.createElement("div");
      sourcesLine.className = "list-meta";
      sourcesLine.textContent = `sources: ${JSON.stringify(tool.guarantee_sources || {})}`;
      item.appendChild(sourcesLine);
      if (runner === "local" && tool.resolved_source === "binding") {
        const sandboxLine = document.createElement("div");
        sandboxLine.className = "list-meta";
        sandboxLine.textContent = `sandbox: ${sandboxEnabled ? "enabled" : "disabled"}`;
        item.appendChild(sandboxLine);
        const sandboxActions = document.createElement("div");
        sandboxActions.className = "control-actions";
        const sandboxBtn = document.createElement("button");
        sandboxBtn.className = "btn ghost small";
        sandboxBtn.textContent = sandboxEnabled ? "Disable sandbox" : "Enable sandbox";
        sandboxBtn.onclick = () => updateSandbox(tool.tool_name, !sandboxEnabled);
        sandboxActions.appendChild(sandboxBtn);
        item.appendChild(sandboxActions);
      }
      if (tool.blocked_reason) {
        const blocked = document.createElement("div");
        blocked.className = "list-meta";
        blocked.textContent = `blocked: ${tool.blocked_reason}`;
        item.appendChild(blocked);
      }
      item.appendChild(_renderOverrides(tool.tool_name, tool.overrides || {}));
      list.appendChild(item);
    });
    container.appendChild(list);
    utils.updateCopyButton("securityCopy", () => JSON.stringify(data, null, 2));
  }

  render.renderSecurity = renderSecurity;
  render.refreshSecurity = refreshSecurity;
  render.applySecurityOverride = applySecurityOverride;
  render.updateSandbox = updateSandbox;
  window.renderSecurity = renderSecurity;
  window.refreshSecurity = refreshSecurity;
})();
