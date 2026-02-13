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

  function citationEntryFromRow(row, mapping) {
    if (!row || typeof row !== "object") return null;
    const citationId =
      typeof row.citation_id === "string" && row.citation_id.trim()
        ? row.citation_id.trim()
        : typeof row.id === "string" && row.id.trim()
          ? row.id.trim()
          : "";
    const titleField = mapping && mapping.primary ? mapping.primary : "title";
    const title = typeof row[titleField] === "string" ? row[titleField].trim() : "";
    const sourceId = typeof row.source_id === "string" ? row.source_id.trim() : "";
    const url = typeof row.url === "string" ? row.url.trim() : "";
    const documentId = typeof row.document_id === "string" ? row.document_id.trim() : "";
    const chunkId = typeof row.chunk_id === "string" ? row.chunk_id.trim() : "";
    const pageNumber = row.page_number ?? row.page;
    if (!title || (!sourceId && !url && !documentId && !chunkId)) {
      return null;
    }
    const entry = { title: title };
    if (citationId) entry.citation_id = citationId;
    if (sourceId) entry.source_id = sourceId;
    if (url) entry.url = url;
    if (documentId) entry.document_id = documentId;
    if (chunkId) entry.chunk_id = chunkId;
    if (typeof row.snippet === "string" && row.snippet.trim()) entry.snippet = row.snippet.trim();
    if (typeof pageNumber === "number" || typeof pageNumber === "string") entry.page_number = pageNumber;
    return entry;
  }

  function interactiveListTarget(node) {
    if (!node || !node.closest) return false;
    return Boolean(node.closest("button, input, a, textarea, select, label"));
  }

  function suggestionMessageFromRow(row, mapping) {
    if (!row || typeof row !== "object") return "";
    const secondaryField =
      mapping && typeof mapping.secondary === "string" && mapping.secondary ? mapping.secondary : "prompt";
    const primaryField = mapping && typeof mapping.primary === "string" && mapping.primary ? mapping.primary : "title";
    const secondaryValue = row[secondaryField];
    if (typeof secondaryValue === "string" && secondaryValue.trim()) return secondaryValue.trim();
    const primaryValue = row[primaryField];
    if (typeof primaryValue === "string" && primaryValue.trim()) return primaryValue.trim();
    return "";
  }

  function resolveSuggestionAction(el) {
    if (!el || typeof el !== "object") return null;
    const source = typeof el.source === "string" ? el.source.trim() : "";
    if (source !== "state.chat.suggestions") return null;
    const studioRoot = window.N3Studio || {};
    const studioState = studioRoot && studioRoot.state ? studioRoot.state : null;
    if (!studioState || typeof studioState.getCachedManifest !== "function") return null;
    const manifest = studioState.getCachedManifest();
    const actions = manifest && manifest.actions && typeof manifest.actions === "object" ? manifest.actions : null;
    if (!actions) return null;
    const rows = Object.values(actions)
      .filter((entry) => entry && typeof entry === "object" && entry.type === "chat.message.send")
      .sort((left, right) => String((left && left.id) || "").localeCompare(String((right && right.id) || "")));
    const chosen = rows[0];
    if (!chosen || typeof chosen.id !== "string" || !chosen.id) return null;
    return { id: chosen.id, type: "chat.message.send" };
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
    const suggestionAction = resolveSuggestionAction(el);

    if (!rows.length) {
      const empty = document.createElement("div");
      empty.className = "ui-empty-state";
      const emptyState = el.empty_state || {};
      const title = emptyState.title;
      const text = emptyState.text || el.empty_text || "No items yet.";
      if (title) {
        const titleEl = document.createElement("div");
        titleEl.className = "ui-empty-state-title";
        titleEl.textContent = title;
        empty.appendChild(titleEl);
      }
      const textEl = document.createElement("div");
      textEl.className = "ui-empty-state-text";
      textEl.textContent = text;
      empty.appendChild(textEl);
      listWrap.appendChild(empty);
      wrapper.appendChild(listWrap);
      return wrapper;
    }

    rows.forEach((row) => {
      const rowId = idField ? row[idField] : null;
      const item = document.createElement("div");
      item.className = `ui-list-item ui-list-${variant}`;
      const citationEntry = citationEntryFromRow(row, mapping);
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
      if (citationEntry) {
        item.classList.add("ui-list-citation-item");
        if (typeof citationEntry.citation_id === "string" && citationEntry.citation_id) {
          item.dataset.citationId = citationEntry.citation_id;
        }
        item.addEventListener("click", (event) => {
          if (interactiveListTarget(event.target)) return;
          if (typeof citationEntry.citation_id === "string" && citationEntry.citation_id && typeof root.selectCitationId === "function") {
            root.selectCitationId(citationEntry.citation_id);
          }
          if (typeof root.focusDrawerPreviewForCitation === "function") {
            root.focusDrawerPreviewForCitation(citationEntry, item);
            return;
          }
          if (typeof root.openCitationPreview === "function") {
            root.openCitationPreview(citationEntry, item, [citationEntry]);
          }
        });
      }
      if (suggestionAction && !citationEntry) {
        item.classList.add("ui-list-suggestion-item");
        item.addEventListener("click", (event) => {
          if (interactiveListTarget(event.target)) return;
          const message = suggestionMessageFromRow(row, mapping);
          if (!message) return;
          handleAction(suggestionAction, { message: message, source: "suggestion" }, item);
        });
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
      empty.className = "ui-empty-state";
      const emptyState = el.empty_state || {};
      const title = emptyState.title;
      const text = emptyState.text || el.empty_text || "No rows yet.";
      if (title) {
        const titleEl = document.createElement("div");
        titleEl.className = "ui-empty-state-title";
        titleEl.textContent = title;
        empty.appendChild(titleEl);
      }
      const textEl = document.createElement("div");
      textEl.className = "ui-empty-state-text";
      textEl.textContent = text;
      empty.appendChild(textEl);
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
