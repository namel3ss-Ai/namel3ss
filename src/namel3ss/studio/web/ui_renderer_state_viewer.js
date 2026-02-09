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

    wrap.appendChild(createRow("Target", String(backend.target || "memory")));
    wrap.appendChild(createRow("Kind", String(backend.kind || "memory")));
    wrap.appendChild(createRow("Durable", backend.durable ? "yes" : "no"));
    wrap.appendChild(createRow("Deterministic", backend.deterministic_ordering ? "yes" : "no"));
    wrap.appendChild(createRow("State Schema", schemaVersion || "state_schema@1"));
    wrap.appendChild(createRow("Pending Migrations", migration.pending ? "yes" : "no"));
    wrap.appendChild(createRow("Applied Plan", String(migration.applied_plan_id || "none")));

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
    });
    details.appendChild(summary);
    details.appendChild(pre);
    wrap.appendChild(details);

    return wrap;
  }

  window.N3UIRender = window.N3UIRender || {};
  window.N3UIRender.renderStateInspectorElement = renderStateInspectorElement;
})();
