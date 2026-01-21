(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const dom = root.dom;
  const dataView = root.data || (root.data = {});

  function stableClone(value) {
    if (Array.isArray(value)) {
      return value.map((item) => stableClone(item));
    }
    if (value && typeof value === "object") {
      const next = {};
      Object.keys(value)
        .sort()
        .forEach((key) => {
          next[key] = stableClone(value[key]);
        });
      return next;
    }
    return value;
  }

  function stableStringify(value) {
    try {
      return JSON.stringify(stableClone(value), null, 2);
    } catch (err) {
      return String(value);
    }
  }

  function isEmptyObject(value) {
    return !value || typeof value !== "object" || Array.isArray(value) ? false : Object.keys(value).length === 0;
  }

  function buildSection(titleText) {
    const section = document.createElement("section");
    section.className = "data-section";
    const heading = document.createElement("div");
    heading.className = "data-title";
    heading.textContent = titleText || "Data";
    section.appendChild(heading);
    return { section, heading };
  }

  function formatList(values) {
    if (!Array.isArray(values) || !values.length) return "none";
    return values.map((value) => String(value)).join(", ");
  }

  function appendListItem(list, label, value) {
    const row = document.createElement("div");
    row.className = "list-item";
    row.textContent = `${label}: ${value}`;
    list.appendChild(row);
  }

  function renderAuthSection(sessionPayload) {
    const { section } = buildSection("Authentication");
    const auth = sessionPayload && sessionPayload.auth ? sessionPayload.auth : null;
    if (!auth) {
      section.appendChild(dom.buildEmpty("No authentication data yet."));
      return section;
    }
    const list = document.createElement("div");
    list.className = "list";
    appendListItem(list, "Status", auth.authenticated ? "authenticated" : "unauthenticated");
    if (auth.source) appendListItem(list, "Source", auth.source);
    if (auth.error) appendListItem(list, "Error", auth.error);
    if (auth.token) {
      const tokenStatus = auth.token_status ? `${auth.token_status} | ${auth.token}` : auth.token;
      appendListItem(list, "Token", tokenStatus);
    } else if (auth.token_status) {
      appendListItem(list, "Token status", auth.token_status);
    }
    const session = sessionPayload.session || null;
    if (session) {
      const sessionBits = [];
      if (session.id) sessionBits.push(session.id);
      if (session.status) sessionBits.push(session.status);
      if (Number.isInteger(session.created_tick)) sessionBits.push(`created ${session.created_tick}`);
      if (Number.isInteger(session.expires_at)) sessionBits.push(`expires ${session.expires_at}`);
      if (sessionBits.length) {
        appendListItem(list, "Session", sessionBits.join(" | "));
      }
    }
    section.appendChild(list);
    return section;
  }

  function renderIdentitySection(sessionPayload) {
    const { section } = buildSection("Identity");
    const identity = sessionPayload && sessionPayload.identity ? sessionPayload.identity : null;
    if (!identity) {
      section.appendChild(dom.buildEmpty("No identity resolved."));
      return section;
    }
    const list = document.createElement("div");
    list.className = "list";
    appendListItem(list, "Subject", identity.subject || "none");
    appendListItem(list, "Roles", formatList(identity.roles));
    appendListItem(list, "Permissions", formatList(identity.permissions));
    appendListItem(list, "Trust level", identity.trust_level || "none");
    section.appendChild(list);
    return section;
  }

  function formatBackendStatus(backend) {
    if (!backend || typeof backend !== "object") {
      return { target: "memory", kind: "unknown", enabled: "false", descriptor: "none", replicas: "none" };
    }
    const replicas = Array.isArray(backend.replicas) && backend.replicas.length ? backend.replicas.join(", ") : "none";
    return {
      target: backend.target || "memory",
      kind: backend.kind || "unknown",
      enabled: backend.enabled ? "true" : "false",
      descriptor: backend.descriptor || "none",
      replicas,
    };
  }

  function formatExportSummary(summary) {
    if (!summary || typeof summary !== "object") return "none";
    const ok = summary.ok === false ? "errors" : "ok";
    const total = Number.isInteger(summary.total) ? summary.total : 0;
    const parts = [ok, `${total} records`];
    if (summary.destination) parts.push(String(summary.destination));
    return parts.join(" | ");
  }

  function formatImportSummary(summary) {
    if (!summary || typeof summary !== "object") return "none";
    const ok = summary.ok === false ? "errors" : "ok";
    const records = Array.isArray(summary.records) ? summary.records.reduce((acc, item) => acc + (item && item.count ? Number(item.count) : 0), 0) : 0;
    const errors = Array.isArray(summary.errors) ? summary.errors.length : 0;
    const parts = [ok, `${records} records`];
    if (errors) parts.push(`${errors} errors`);
    return parts.join(" | ");
  }

  function renderBackendSection(dataStatus) {
    const { section } = buildSection("Backends");
    if (!dataStatus) {
      section.appendChild(dom.buildEmpty("No backend status yet."));
      return section;
    }
    if (dataStatus.ok === false) {
      section.appendChild(dom.buildEmpty(dataStatus.error || "Unable to load backend status."));
      return section;
    }
    const list = document.createElement("div");
    list.className = "list";
    const backend = formatBackendStatus(dataStatus.backend);
    appendListItem(list, "Target", backend.target);
    appendListItem(list, "Kind", backend.kind);
    appendListItem(list, "Enabled", backend.enabled);
    if (backend.descriptor && backend.descriptor !== "none") {
      appendListItem(list, "Descriptor", backend.descriptor);
    }
    appendListItem(list, "Replicas", backend.replicas);
    appendListItem(list, "Last export", formatExportSummary(dataStatus.export));
    appendListItem(list, "Last import", formatImportSummary(dataStatus.import));
    section.appendChild(list);
    return section;
  }

  function formatPlanChange(change) {
    if (!change || typeof change !== "object") return "";
    const kind = change.kind || "";
    const record = change.record || "";
    const field = change.field || "";
    if (kind === "record_removed") return `record "${record}" removed`;
    if (kind === "record_added") return `record "${record}" added`;
    if (kind === "record_tenant_key_changed") return `record "${record}" tenant key updated`;
    if (kind === "record_ttl_changed") return `record "${record}" ttl updated`;
    if (kind === "field_removed") return `record "${record}" field "${field}" removed`;
    if (kind === "field_added_required") return `record "${record}" added required field "${field}"`;
    if (kind === "field_added_optional") return `record "${record}" added optional field "${field}"`;
    if (kind === "field_type_changed") return `record "${record}" field "${field}" type updated`;
    if (kind === "field_constraint_changed") return `record "${record}" field "${field}" constraint updated`;
    return `${kind} on record ${record}`;
  }

  function renderMigrationsSection(statusPayload, planPayload) {
    const { section } = buildSection("Migrations");
    if (!statusPayload) {
      section.appendChild(dom.buildEmpty("No migration status yet."));
      return section;
    }
    if (statusPayload.ok === false) {
      section.appendChild(dom.buildEmpty(statusPayload.error || "Unable to load migration status."));
      return section;
    }
    const list = document.createElement("div");
    list.className = "list";
    appendListItem(list, "Plan", statusPayload.plan_id || "none");
    appendListItem(list, "Applied", statusPayload.applied_plan_id || "none");
    appendListItem(list, "Pending", statusPayload.pending ? "yes" : "no");
    appendListItem(list, "Breaking", statusPayload.breaking ? "yes" : "no");
    appendListItem(list, "Reversible", statusPayload.reversible ? "yes" : "no");
    if (statusPayload.plan_changed) {
      appendListItem(list, "Plan changed", "yes");
    }
    section.appendChild(list);
    if (planPayload && planPayload.ok === false) {
      section.appendChild(dom.buildEmpty(planPayload.error || "Unable to load migration plan."));
      return section;
    }
    const plan = planPayload && planPayload.plan ? planPayload.plan : null;
    const changes = plan && Array.isArray(plan.changes) ? plan.changes : [];
    if (!changes.length) {
      section.appendChild(dom.buildEmpty("No migration changes listed."));
      return section;
    }
    const changeList = document.createElement("div");
    changeList.className = "list";
    const limit = 6;
    changes.slice(0, limit).forEach((change) => {
      const text = formatPlanChange(change);
      if (!text) return;
      appendListItem(changeList, "Change", text);
    });
    if (changes.length > limit) {
      appendListItem(changeList, "More", `${changes.length - limit} additional changes`);
    }
    section.appendChild(changeList);
    return section;
  }

  function formatIds(ids, limit = 6) {
    const list = Array.isArray(ids) ? ids.slice(0, limit) : [];
    const text = list.map((item) => String(item)).join(", ");
    if (Array.isArray(ids) && ids.length > limit) {
      return `${text}, ...`;
    }
    return text;
  }

  function formatAction(action) {
    if (!action || typeof action !== "object") return "";
    const parts = [];
    if (action.type) parts.push(action.type);
    if (action.flow) parts.push(`flow "${action.flow}"`);
    if (action.record) parts.push(`record "${action.record}"`);
    if (action.target) parts.push(`target "${action.target}"`);
    if (!parts.length && action.id) parts.push(action.id);
    return parts.join(" | ");
  }

  function renderEffectsSection(effects) {
    const { section } = buildSection("Latest effects");
    if (!effects || typeof effects !== "object") {
      section.appendChild(dom.buildEmpty("No record changes recorded yet."));
      return section;
    }
    const actionLabel = formatAction(effects.action);
    if (actionLabel) {
      const actionLine = document.createElement("div");
      actionLine.className = "data-empty";
      actionLine.textContent = `Action: ${actionLabel}`;
      section.appendChild(actionLine);
    }
    const records = Array.isArray(effects.records) ? effects.records : [];
    if (!records.length) {
      section.appendChild(dom.buildEmpty("No record changes recorded yet."));
      return section;
    }
    const list = document.createElement("div");
    list.className = "list";
    records.forEach((change) => {
      if (!change || !change.record || !change.action) return;
      const line = document.createElement("div");
      line.className = "list-item";
      const ids = Array.isArray(change.ids) && change.ids.length ? ` (ids: ${formatIds(change.ids)})` : "";
      const count = Number.isInteger(change.count) ? change.count : Array.isArray(change.ids) ? change.ids.length : 0;
      line.textContent = `${change.record}: ${change.action} ${count}${ids}`;
      list.appendChild(line);
    });
    if (!list.children.length) {
      section.appendChild(dom.buildEmpty("No record changes recorded yet."));
      return section;
    }
    section.appendChild(list);
    return section;
  }

  function renderStateSection(stateValue) {
    const { section } = buildSection("State");
    if (!stateValue || isEmptyObject(stateValue)) {
      section.appendChild(dom.buildEmpty("No state yet."));
      return section;
    }
    const block = document.createElement("pre");
    block.className = "code-block";
    block.textContent = stableStringify(stateValue);
    section.appendChild(block);
    return section;
  }

  function flattenElements(elements) {
    const list = [];
    (elements || []).forEach((element) => {
      list.push(element);
      if (Array.isArray(element.children)) {
        list.push(...flattenElements(element.children));
      }
    });
    return list;
  }

  function collectTables(manifest) {
    const tables = [];
    if (!manifest || !manifest.pages) return tables;
    manifest.pages.forEach((page) => {
      const elements = flattenElements(page.elements || []);
      elements.forEach((element) => {
        if (element.type === "table") tables.push(element);
      });
    });
    return tables;
  }

  function buildTableElement(table) {
    const wrap = document.createElement("div");
    wrap.className = "data-table-wrap";
    const htmlTable = document.createElement("table");
    htmlTable.className = "ui-table data-table";

    const columns = Array.isArray(table.columns) ? table.columns : [];
    const rows = Array.isArray(table.rows) ? table.rows : [];
    const pageSize = table.pagination && Number.isInteger(table.pagination.page_size) ? table.pagination.page_size : null;
    const displayRows = pageSize ? rows.slice(0, pageSize) : rows;
    if (!columns.length) {
      wrap.appendChild(dom.buildEmpty("No columns available."));
      return wrap;
    }

    const header = document.createElement("tr");
    columns.forEach((column) => {
      const th = document.createElement("th");
      th.textContent = column.label || column.name;
      header.appendChild(th);
    });
    htmlTable.appendChild(header);

    if (!displayRows.length) {
      const empty = document.createElement("div");
      empty.className = "data-empty";
      empty.textContent = table.empty_text || "No rows yet.";
      wrap.appendChild(empty);
      return wrap;
    }

    displayRows.forEach((row) => {
      const tr = document.createElement("tr");
      columns.forEach((column) => {
        const td = document.createElement("td");
        td.textContent = row[column.name] ?? "";
        tr.appendChild(td);
      });
      htmlTable.appendChild(tr);
    });

    wrap.appendChild(htmlTable);
    return wrap;
  }

  function renderTable(table) {
    const { section } = buildSection(table.record || "Table");
    section.appendChild(buildTableElement(table));
    return section;
  }

  function buildRecordColumns(entry) {
    const columns = [];
    const fields = Array.isArray(entry.fields) ? entry.fields : [];
    const idField = entry.id_field || "";
    if (idField && !fields.some((field) => field && field.name === idField)) {
      columns.push({ name: idField, label: idField });
    }
    fields.forEach((field) => {
      if (!field || !field.name) return;
      columns.push({ name: field.name, label: field.name });
    });
    return columns;
  }

  function renderRecordSection(entry) {
    const label = entry && entry.name ? String(entry.name) : "Record";
    const count = entry && Number.isInteger(entry.count) ? entry.count : null;
    const title = count !== null ? `${label} (${count})` : label;
    const { section } = buildSection(title);
    if (entry && entry.error) {
      section.appendChild(dom.buildEmpty(entry.error));
      return section;
    }
    const columns = buildRecordColumns(entry || {});
    const rows = Array.isArray(entry && entry.rows) ? entry.rows : [];
    section.appendChild(
      buildTableElement({
        record: label,
        columns,
        rows,
        empty_text: "No rows yet.",
      })
    );
    if (entry && entry.truncated) {
      const limit = Number.isInteger(entry.limit) ? entry.limit : rows.length;
      const note = document.createElement("div");
      note.className = "data-empty";
      note.textContent = `Showing ${limit} of ${count || rows.length}.`;
      section.appendChild(note);
    }
    return section;
  }

  function renderData(payload, nextManifest) {
    const container = document.getElementById("data");
    if (!container) return;
    container.innerHTML = "";
    const cached = state && typeof state.getCachedData === "function" ? state.getCachedData() : null;
    const data = payload || cached;
    const sessionPayload = state && typeof state.getCachedSession === "function" ? state.getCachedSession() : null;
    const dataStatus = state && typeof state.getCachedDataStatus === "function" ? state.getCachedDataStatus() : null;
    const migrationStatus =
      state && typeof state.getCachedMigrationStatus === "function" ? state.getCachedMigrationStatus() : null;
    const migrationPlan = state && typeof state.getCachedMigrationPlan === "function" ? state.getCachedMigrationPlan() : null;
    container.appendChild(renderAuthSection(sessionPayload));
    container.appendChild(renderIdentitySection(sessionPayload));
    container.appendChild(renderBackendSection(dataStatus));
    container.appendChild(renderMigrationsSection(migrationStatus, migrationPlan));
    if (data && data.ok === false) {
      container.appendChild(dom.buildEmpty(data.error || "Unable to load data."));
      return;
    }
    if (data && (Object.prototype.hasOwnProperty.call(data, "state") || Array.isArray(data.records))) {
      container.appendChild(renderEffectsSection(data.effects));
      container.appendChild(renderStateSection(data.state || {}));
      const records = Array.isArray(data.records) ? data.records : [];
      if (!records.length) {
        container.appendChild(dom.buildEmpty("No records available."));
        return;
      }
      records.forEach((entry) => {
        container.appendChild(renderRecordSection(entry));
      });
      return;
    }
    const manifest = nextManifest || (state && state.getCachedManifest ? state.getCachedManifest() : null);
    if (!manifest) {
      dom.showEmpty(container, "No data yet. Run your app.");
      return;
    }
    const tables = collectTables(manifest);
    if (!tables.length) {
      dom.showEmpty(container, "No tables available.");
      return;
    }
    tables.forEach((table) => {
      container.appendChild(renderTable(table));
    });
  }

  dataView.renderData = renderData;
  window.renderData = renderData;
})();
