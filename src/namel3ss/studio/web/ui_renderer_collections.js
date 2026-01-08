(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});

  function rowSnapshot(row, columns) {
    const snapshot = {};
    (columns || []).forEach((c) => {
      snapshot[c.name] = row[c.name] ?? null;
    });
    return snapshot;
  }

  function listSnapshot(row, mapping) {
    const snapshot = {};
    if (!mapping) return snapshot;
    ["primary", "secondary", "meta", "icon"].forEach((key) => {
      const field = mapping[key];
      if (field) snapshot[field] = row[field] ?? null;
    });
    return snapshot;
  }

  function formatListValue(value) {
    if (value === null || value === undefined) return "";
    if (typeof value === "string") return value;
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }

  function renderListElement(el, handleAction) {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-element";
    const listWrap = document.createElement("div");
    listWrap.className = "ui-list";
    const rows = Array.isArray(el.rows) ? el.rows : [];
    const mapping = el.item || {};
    const variant = el.variant || "two_line";
    const actions = Array.isArray(el.actions) ? el.actions : [];
    const selectionMode = el.selection || "none";
    const idField = el.id_field || (rows[0] && (rows[0].id != null ? "id" : rows[0]._id != null ? "_id" : null));
    const selectedIds = new Set();
    const rowMap = new Map();

    if (!rows.length) {
      const empty = document.createElement("div");
      empty.textContent = el.empty_text || "No items yet.";
      listWrap.appendChild(empty);
      wrapper.appendChild(listWrap);
      return wrapper;
    }

    rows.forEach((row) => {
      const rowId = idField ? row[idField] : null;
      const item = document.createElement("div");
      item.className = `ui-list-item ui-list-${variant}`;
      if (selectionMode !== "none") {
        const selectWrap = document.createElement("div");
        selectWrap.className = "ui-list-select";
        const input = document.createElement("input");
        input.type = selectionMode === "multi" ? "checkbox" : "radio";
        input.name = selectionMode === "multi" ? "" : el.id || "list-selection";
        input.ariaLabel = "Select item";
        input.onchange = () => {
          if (selectionMode === "multi") {
            if (input.checked) selectedIds.add(rowId);
            else selectedIds.delete(rowId);
            item.classList.toggle("selected", input.checked);
            return;
          }
          selectedIds.clear();
          if (input.checked) selectedIds.add(rowId);
          rowMap.forEach((node, id) => node.classList.toggle("selected", id === rowId));
        };
        selectWrap.appendChild(input);
        item.appendChild(selectWrap);
      }

      const content = document.createElement("div");
      content.className = "ui-list-content";
      if (variant === "icon" && mapping.icon) {
        const icon = document.createElement("div");
        icon.className = "ui-list-icon";
        icon.textContent = formatListValue(row[mapping.icon]);
        content.appendChild(icon);
      }
      const text = document.createElement("div");
      text.className = "ui-list-text";
      const primaryField = mapping.primary || idField;
      const primaryValue = primaryField ? row[primaryField] : rowId;
      const primary = document.createElement("div");
      primary.className = "ui-list-primary";
      primary.textContent = formatListValue(primaryValue);
      text.appendChild(primary);
      if (variant !== "single_line" && mapping.secondary) {
        const secondary = document.createElement("div");
        secondary.className = "ui-list-secondary";
        secondary.textContent = formatListValue(row[mapping.secondary]);
        text.appendChild(secondary);
      }
      content.appendChild(text);
      if (mapping.meta) {
        const meta = document.createElement("div");
        meta.className = "ui-list-meta";
        meta.textContent = formatListValue(row[mapping.meta]);
        content.appendChild(meta);
      }
      item.appendChild(content);

      if (actions.length) {
        const actionsWrap = document.createElement("div");
        actionsWrap.className = "ui-list-actions";
        actions.forEach((action) => {
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "btn small";
          btn.textContent = action.label || "Run";
          btn.onclick = (e) => {
            const payload = {
              record: el.record,
              record_id: rowId,
              row: listSnapshot(row, mapping),
            };
            if (selectionMode !== "none") {
              payload.selection = {
                mode: selectionMode,
                ids: Array.from(selectedIds),
              };
            }
            handleAction(action, payload, e.currentTarget);
          };
          actionsWrap.appendChild(btn);
        });
        item.appendChild(actionsWrap);
      }

      if (selectionMode === "single" && rowId != null) {
        rowMap.set(rowId, item);
      }
      listWrap.appendChild(item);
    });
    wrapper.appendChild(listWrap);
    return wrapper;
  }

  function renderTableElement(el, handleAction) {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-element";
    const table = document.createElement("table");
    table.className = "ui-table";
    const columns = Array.isArray(el.columns) ? el.columns : [];
    const rows = Array.isArray(el.rows) ? el.rows : [];
    const rowActions = Array.isArray(el.row_actions) ? el.row_actions : [];
    const selectionMode = el.selection || "none";
    const idField = el.id_field || (rows[0] && (rows[0].id != null ? "id" : rows[0]._id != null ? "_id" : null));
    const pageSize = el.pagination && Number.isInteger(el.pagination.page_size) ? el.pagination.page_size : null;
    const displayRows = pageSize ? rows.slice(0, pageSize) : rows;

    if (!columns.length) {
      const empty = document.createElement("div");
      empty.textContent = "No columns available.";
      wrapper.appendChild(empty);
      return wrapper;
    }
    if (!displayRows.length) {
      const empty = document.createElement("div");
      empty.textContent = el.empty_text || "No rows yet.";
      wrapper.appendChild(empty);
      return wrapper;
    }

    const selectedIds = new Set();
    const rowMap = new Map();

    const header = document.createElement("tr");
    if (selectionMode !== "none") {
      const th = document.createElement("th");
      th.textContent = "";
      header.appendChild(th);
    }
    columns.forEach((c) => {
      const th = document.createElement("th");
      th.textContent = c.label || c.name;
      header.appendChild(th);
    });
    if (rowActions.length) {
      const th = document.createElement("th");
      th.textContent = "Actions";
      header.appendChild(th);
    }
    table.appendChild(header);

    displayRows.forEach((row) => {
      const tr = document.createElement("tr");
      const rowId = idField ? row[idField] : null;
      if (selectionMode !== "none") {
        const td = document.createElement("td");
        const input = document.createElement("input");
        input.type = selectionMode === "multi" ? "checkbox" : "radio";
        input.name = selectionMode === "multi" ? "" : el.id || "table-selection";
        input.ariaLabel = "Select row";
        input.onchange = () => {
          if (selectionMode === "multi") {
            if (input.checked) selectedIds.add(rowId);
            else selectedIds.delete(rowId);
            tr.classList.toggle("selected", input.checked);
            return;
          }
          selectedIds.clear();
          if (input.checked) selectedIds.add(rowId);
          rowMap.forEach((node, id) => node.classList.toggle("selected", id === rowId));
        };
        td.appendChild(input);
        tr.appendChild(td);
      }
      columns.forEach((c) => {
        const td = document.createElement("td");
        td.textContent = row[c.name] ?? "";
        tr.appendChild(td);
      });
      if (rowActions.length) {
        const td = document.createElement("td");
        const actionsWrap = document.createElement("div");
        actionsWrap.className = "ui-row-actions";
        rowActions.forEach((action) => {
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "btn small";
          btn.textContent = action.label || "Run";
          btn.onclick = (e) => {
            const payload = {
              record: el.record,
              record_id: rowId,
              row: rowSnapshot(row, columns),
            };
            if (selectionMode !== "none") {
              payload.selection = {
                mode: selectionMode,
                ids: Array.from(selectedIds),
              };
            }
            handleAction(action, payload, e.currentTarget);
          };
          actionsWrap.appendChild(btn);
        });
        td.appendChild(actionsWrap);
        tr.appendChild(td);
      }
      if (selectionMode === "single" && rowId != null) {
        rowMap.set(rowId, tr);
      }
      table.appendChild(tr);
    });
    wrapper.appendChild(table);
    return wrapper;
  }

  root.renderListElement = renderListElement;
  root.renderTableElement = renderTableElement;
})();
