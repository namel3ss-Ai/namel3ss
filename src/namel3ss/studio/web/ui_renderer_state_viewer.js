(function () {
  function createRow(label, value) {
    const row = document.createElement("div");
    row.className = "ui-state-inspector-row";
    const keyNode = document.createElement("span");
    keyNode.className = "ui-state-inspector-key";
    keyNode.textContent = label;
    const valueNode = document.createElement("span");
    valueNode.className = "ui-state-inspector-value";
    valueNode.textContent = value;
    row.appendChild(keyNode);
    row.appendChild(valueNode);
    return row;
  }

  function stringify(value) {
    try {
      return JSON.stringify(value, null, 2);
    } catch (_err) {
      return "{}";
    }
  }

  function renderStateInspectorElement(el) {
    const wrap = document.createElement("section");
    wrap.className = "ui-state-inspector ui-element";

    const title = document.createElement("h3");
    title.className = "ui-state-inspector-title";
    title.textContent = "State Inspector";
    wrap.appendChild(title);

    const backend = el && typeof el.persistence_backend === "object" && el.persistence_backend ? el.persistence_backend : {};
    const migration = el && typeof el.migration_status === "object" && el.migration_status ? el.migration_status : {};
    const schemaVersion = typeof el.state_schema_version === "string" ? el.state_schema_version : "";
    const uiState = el && typeof el.ui_state === "object" && el.ui_state ? el.ui_state : {};
    const uiStateRows = normalizeUIStateRows(uiState);
    const appPermissions = el && typeof el.app_permissions === "object" && el.app_permissions ? el.app_permissions : {};
    const appPermissionRows = normalizeAppPermissionRows(appPermissions);
    const permissionWarnings = Array.isArray(appPermissions.warnings) ? appPermissions.warnings : [];
    const permissionMode = typeof appPermissions.mode === "string" ? appPermissions.mode : "none";

    wrap.appendChild(createRow("Target", String(backend.target || "memory")));
    wrap.appendChild(createRow("Kind", String(backend.kind || "memory")));
    wrap.appendChild(createRow("Durable", backend.durable ? "yes" : "no"));
    wrap.appendChild(createRow("Deterministic", backend.deterministic_ordering ? "yes" : "no"));
    wrap.appendChild(createRow("State Schema", schemaVersion || "state_schema@1"));
    wrap.appendChild(createRow("Pending Migrations", migration.pending ? "yes" : "no"));
    wrap.appendChild(createRow("Applied Plan", String(migration.applied_plan_id || "none")));
    wrap.appendChild(createRow("UI State Keys", String(uiStateRows.length)));
    wrap.appendChild(createRow("Permissions Mode", permissionMode));
    wrap.appendChild(createRow("Permissions Used", String(appPermissionRows.length)));
    wrap.appendChild(createRow("Permission Warnings", String(permissionWarnings.length)));

    if (uiStateRows.length) {
      const stateBlock = document.createElement("details");
      stateBlock.className = "ui-state-inspector-details";
      const stateSummary = document.createElement("summary");
      stateSummary.textContent = "Declared UI state";
      stateBlock.appendChild(stateSummary);
      const list = document.createElement("div");
      list.className = "ui-state-inspector-json";
      uiStateRows.forEach((entry) => {
        const row = document.createElement("div");
        row.className = "ui-state-inspector-row";
        const left = document.createElement("span");
        left.className = "ui-state-inspector-key";
        left.textContent = `${entry.path} (${entry.scope})`;
        const right = document.createElement("span");
        right.className = "ui-state-inspector-value";
        right.textContent = `${entry.type} · ${entry.source} · ${stringifyInline(entry.value)}`;
        row.appendChild(left);
        row.appendChild(right);
        list.appendChild(row);
      });
      stateBlock.appendChild(list);
      wrap.appendChild(stateBlock);
    }
    if (appPermissionRows.length || permissionWarnings.length) {
      const permissionsBlock = document.createElement("details");
      permissionsBlock.className = "ui-state-inspector-details";
      const permissionsSummary = document.createElement("summary");
      permissionsSummary.textContent = "Application permissions";
      permissionsBlock.appendChild(permissionsSummary);
      const list = document.createElement("div");
      list.className = "ui-state-inspector-json";
      appPermissionRows.forEach((entry) => {
        const row = document.createElement("div");
        row.className = "ui-state-inspector-row";
        const left = document.createElement("span");
        left.className = "ui-state-inspector-key";
        left.textContent = entry.permission;
        const right = document.createElement("span");
        right.className = "ui-state-inspector-value";
        right.textContent = entry.reason;
        row.appendChild(left);
        row.appendChild(right);
        list.appendChild(row);
      });
      permissionWarnings.forEach((warning) => {
        const row = document.createElement("div");
        row.className = "ui-state-inspector-row";
        const left = document.createElement("span");
        left.className = "ui-state-inspector-key";
        left.textContent = "warning";
        const right = document.createElement("span");
        right.className = "ui-state-inspector-value";
        right.textContent = String(warning);
        row.appendChild(left);
        row.appendChild(right);
        list.appendChild(row);
      });
      permissionsBlock.appendChild(list);
      wrap.appendChild(permissionsBlock);
    }

    const details = document.createElement("details");
    details.className = "ui-state-inspector-details";
    const summary = document.createElement("summary");
    summary.textContent = "Persisted state snapshot";
    const pre = document.createElement("pre");
    pre.className = "ui-state-inspector-json";
    pre.textContent = stringify({
      persistence_backend: backend,
      migration_status: migration,
      state_schema_version: schemaVersion || "state_schema@1",
      ui_state: uiState,
      app_permissions: appPermissions,
    });
    details.appendChild(summary);
    details.appendChild(pre);
    wrap.appendChild(details);

    return wrap;
  }

  function stringifyInline(value) {
    if (value === null) return "null";
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    try {
      return JSON.stringify(value);
    } catch (_err) {
      return "{}";
    }
  }

  function normalizeUIStateRows(uiState) {
    const fields = uiState && Array.isArray(uiState.fields) ? uiState.fields : [];
    const valuesByScope = uiState && typeof uiState.values === "object" && uiState.values ? uiState.values : {};
    const rows = [];
    fields.forEach((entry) => {
      if (!entry || typeof entry !== "object") return;
      const path = typeof entry.path === "string" ? entry.path : "";
      const key = typeof entry.key === "string" ? entry.key : "";
      const scope = typeof entry.scope === "string" ? entry.scope : "";
      const type = typeof entry.type === "string" ? entry.type : "";
      const source = entry.source === "restored" ? "restored" : "default";
      if (!path || !key || !scope || !type) return;
      const scopeValues = valuesByScope && typeof valuesByScope[scope] === "object" && valuesByScope[scope] ? valuesByScope[scope] : {};
      rows.push({
        path,
        key,
        scope,
        type,
        source,
        value: scopeValues[key],
      });
    });
    return rows;
  }

  function normalizeAppPermissionRows(payload) {
    const usage = payload && Array.isArray(payload.usage) ? payload.usage : [];
    const rows = [];
    usage.forEach((entry) => {
      if (!entry || typeof entry !== "object") return;
      const permission = typeof entry.permission === "string" ? entry.permission : "";
      const reason = typeof entry.reason === "string" ? entry.reason : "";
      if (!permission || !reason) return;
      rows.push({ permission, reason });
    });
    rows.sort((a, b) => {
      if (a.permission < b.permission) return -1;
      if (a.permission > b.permission) return 1;
      if (a.reason < b.reason) return -1;
      if (a.reason > b.reason) return 1;
      return 0;
    });
    return rows;
  }

  window.N3UIRender = window.N3UIRender || {};
  window.N3UIRender.renderStateInspectorElement = renderStateInspectorElement;
})();
