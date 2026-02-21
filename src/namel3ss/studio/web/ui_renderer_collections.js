(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});

  function rowSnapshot(row, columns) {
    const snapshot = {};
    if (!row || typeof row !== "object") {
      return snapshot;
    }
    (columns || []).forEach((c) => {
      snapshot[c.name] = row[c.name] ?? null;
    });
    return snapshot;
  }

  function listSnapshot(row, mapping) {
    const snapshot = {};
    if (!row || typeof row !== "object") return snapshot;
    if (!mapping) return snapshot;
    ["primary", "secondary", "meta", "icon", "icon_color"].forEach((key) => {
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

  function iconFallbackGlyph(name) {
    const value = formatListValue(name).trim();
    if (!value) return "?";
    return value.slice(0, 1).toUpperCase();
  }

  function createListIconNode(value) {
    if (typeof root.createIconNode === "function") {
      return root.createIconNode(formatListValue(value), { size: "small", decorative: true });
    }
    const fallback = document.createElement("span");
    fallback.className = "ui-list-icon-fallback";
    fallback.textContent = iconFallbackGlyph(value);
    return fallback;
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

  function actionLabel(action) {
    if (!action || typeof action !== "object") return "";
    return typeof action.label === "string" ? action.label.trim().toLowerCase() : "";
  }

  function actionBehavior(action) {
    if (!action || typeof action !== "object") return "";
    const value = typeof action.ui_behavior === "string" ? action.ui_behavior.trim().toLowerCase() : "";
    return value;
  }

  function resolveRenameAction(actions) {
    if (!Array.isArray(actions) || !actions.length) return null;
    const explicit = actions.find((action) => actionBehavior(action) === "rename_modal");
    if (explicit) return explicit;
    return actions.find((action) => actionLabel(action).startsWith("rename")) || null;
  }

  function isRenameAction(action) {
    const behavior = actionBehavior(action);
    if (behavior) return behavior === "rename_modal";
    return actionLabel(action).startsWith("rename");
  }

  function isDestructiveAction(action) {
    const behavior = actionBehavior(action);
    if (behavior) return behavior === "confirm_destructive";
    const label = actionLabel(action);
    return label.includes("delete");
  }

  function isMoveToProjectAction(action) {
    const behavior = actionBehavior(action);
    if (behavior) return behavior === "project_picker";
    const label = actionLabel(action);
    return label.startsWith("move to project");
  }

  function isUploadPickerAction(action) {
    const behavior = actionBehavior(action);
    if (behavior) return behavior === "upload_picker";
    return actionLabel(action).startsWith("upload");
  }

  function findEnabledUploadInput(scope) {
    if (!scope || typeof scope.querySelectorAll !== "function") return null;
    const inputs = Array.from(scope.querySelectorAll("input.ui-upload-input[type='file']"));
    for (const input of inputs) {
      if (!input || input.disabled === true) continue;
      if (input.isConnected === false) continue;
      return input;
    }
    return null;
  }

  function cloneActionPayload(payload) {
    if (!payload || typeof payload !== "object") return {};
    try {
      return JSON.parse(JSON.stringify(payload));
    } catch {
      return { ...payload };
    }
  }

  function openUploadPickerFromActionTarget(target, options) {
    let input = null;
    if (target && typeof target.closest === "function") {
      const section = target.closest(".ui-section");
      input = findEnabledUploadInput(section);
      if (!input) {
        const panel = target.closest(".n3-layout-sidebar, .n3-layout-main, .n3-layout-drawer");
        input = findEnabledUploadInput(panel);
      }
    }
    if (!input) {
      input = findEnabledUploadInput(document);
    }
    if (!input) return false;
    const postAction =
      options && options.postAction && typeof options.postAction === "object" ? options.postAction : null;
    if (postAction && typeof postAction.id === "string" && postAction.id) {
      input.__n3UploadPickerPostAction = {
        id: postAction.id,
        type: typeof postAction.type === "string" && postAction.type ? postAction.type : "call_flow",
        payload: cloneActionPayload(postAction.payload),
      };
    } else {
      input.__n3UploadPickerPostAction = null;
    }
    const openPicker = typeof root.openUploadInputPicker === "function" ? root.openUploadInputPicker : null;
    if (openPicker) {
      return openPicker(input) === true;
    }
    if (typeof input.click === "function") {
      input.click();
      return true;
    }
    return false;
  }

  function resolveRenameValue(payload) {
    const row = payload && payload.row && typeof payload.row === "object" ? payload.row : {};
    const candidates = [row.name, row.source_name, row.file_name, payload && payload.name];
    for (const candidate of candidates) {
      if (typeof candidate === "string" && candidate.trim()) return candidate.trim();
    }
    return "";
  }

  function resolveRenameTitle(payload) {
    const row = payload && payload.row && typeof payload.row === "object" ? payload.row : {};
    if (typeof row.upload_id === "string" && row.upload_id.trim()) {
      return "Rename file";
    }
    return "Rename project";
  }

  function withRenameFields(payload, nextValue) {
    const base = payload && typeof payload === "object" ? { ...payload } : {};
    base.name = nextValue;
    base.project_name = nextValue;
    base.source_name = nextValue;
    base.file_name = nextValue;
    const row = base.row && typeof base.row === "object" ? base.row : {};
    if (typeof row.upload_id === "string" && row.upload_id) {
      base.upload_id = row.upload_id;
    }
    if (typeof row.id === "string" && row.id) {
      base.project_id = row.id;
    }
    return base;
  }

  function openRenameModal(options) {
    const title = options && typeof options.title === "string" ? options.title : "Rename";
    const initialValue = options && typeof options.initialValue === "string" ? options.initialValue : "";
    const onSave = options && typeof options.onSave === "function" ? options.onSave : null;
    if (!onSave) {
      return Promise.resolve(false);
    }
    return new Promise((resolve) => {
      const backdrop = document.createElement("div");
      backdrop.className = "ui-action-modal-backdrop";
      const modal = document.createElement("div");
      modal.className = "ui-action-modal";
      modal.setAttribute("role", "dialog");
      modal.setAttribute("aria-modal", "true");
      modal.setAttribute("aria-label", title);

      const heading = document.createElement("div");
      heading.className = "ui-action-modal-title";
      heading.textContent = title;

      const input = document.createElement("input");
      input.type = "text";
      input.className = "ui-action-modal-input";
      input.value = initialValue;
      input.setAttribute("aria-label", title);

      const error = document.createElement("div");
      error.className = "ui-action-modal-error";
      error.textContent = "";

      const actions = document.createElement("div");
      actions.className = "ui-action-modal-actions";

      const cancelButton = document.createElement("button");
      cancelButton.type = "button";
      cancelButton.className = "btn small ghost";
      cancelButton.textContent = "Cancel";

      const saveButton = document.createElement("button");
      saveButton.type = "button";
      saveButton.className = "btn small primary ui-action-modal-save";
      saveButton.textContent = "Save";

      actions.appendChild(cancelButton);
      actions.appendChild(saveButton);
      modal.appendChild(heading);
      modal.appendChild(input);
      modal.appendChild(error);
      modal.appendChild(actions);
      backdrop.appendChild(modal);
      document.body.appendChild(backdrop);

      let finished = false;
      let saving = false;
      const close = (result) => {
        if (finished) return;
        finished = true;
        document.removeEventListener("keydown", onKeyDown, true);
        if (backdrop.parentNode) {
          backdrop.parentNode.removeChild(backdrop);
        }
        resolve(result);
      };

      const submit = async () => {
        if (saving) return;
        const nextValue = typeof input.value === "string" ? input.value.trim() : "";
        if (!nextValue) {
          error.textContent = "Name can't be empty.";
          input.focus();
          return;
        }
        saving = true;
        error.textContent = "";
        saveButton.disabled = true;
        cancelButton.disabled = true;
        saveButton.classList.add("is-loading");
        saveButton.textContent = "Saving...";
        try {
          await onSave(nextValue);
          close(true);
        } catch (_err) {
          saveButton.disabled = false;
          cancelButton.disabled = false;
          saveButton.classList.remove("is-loading");
          saveButton.textContent = "Save";
          error.textContent = "Rename failed. Try again.";
          saving = false;
          input.focus();
        }
      };

      const onKeyDown = (event) => {
        if (saving) return;
        if (event.key === "Escape") {
          event.preventDefault();
          close(false);
          return;
        }
        if (event.key === "Enter") {
          event.preventDefault();
          submit();
        }
      };

      cancelButton.onclick = () => {
        if (saving) return;
        close(false);
      };
      saveButton.onclick = () => submit();
      backdrop.addEventListener("click", (event) => {
        if (saving) return;
        if (event.target === backdrop) {
          close(false);
        }
      });
      document.addEventListener("keydown", onKeyDown, true);

      input.focus();
      input.select();
    });
  }

  function projectRowsForActionPrompt() {
    const rowsByRecord = root.__listRowsByRecord && typeof root.__listRowsByRecord === "object" ? root.__listRowsByRecord : {};
    const projectsById = new Map();
    Object.entries(rowsByRecord).forEach(([recordName, rows]) => {
      if (!Array.isArray(rows)) return;
      const recordKey = String(recordName || "").toLowerCase();
      rows.forEach((row) => {
        if (!row || typeof row !== "object") return;
        const id = textValue(row.id) || textValue(row.project_id) || textValue(row.projectId);
        if (!id) return;
        const name = textValue(row.name) || textValue(row.project_name) || textValue(row.projectName) || id;
        const hasDocumentFields = Boolean(
          textValue(row.upload_id) ||
            textValue(row.uploadId) ||
            textValue(row.document_id) ||
            textValue(row.documentId) ||
            textValue(row.source_name) ||
            textValue(row.sourceName)
        );
        const recordLooksProject = /project/.test(recordKey) && !/knowledge|document|library|file/.test(recordKey);
        const rowLooksProject = Boolean(name && !hasDocumentFields);
        if (!recordLooksProject && !rowLooksProject) return;
        const next = {
          id: id,
          name: name,
          active: row.active === true || row.is_active === true || row.selected === true,
        };
        const existing = projectsById.get(id);
        if (!existing || (!existing.active && next.active)) {
          projectsById.set(id, next);
        }
      });
    });
    return Array.from(projectsById.values());
  }

  function textValue(value) {
    if (typeof value !== "string") return "";
    const trimmed = value.trim();
    return trimmed ? trimmed : "";
  }

  function promptProjectDestination() {
    const projects = projectRowsForActionPrompt();
    if (!projects.length) return null;
    const active = projects.find((entry) => entry.active) || projects[0];
    const help = projects.map((entry) => `- ${entry.id} (${entry.name})`).join("\n");
    const raw = window.prompt(`Move file to project. Type project id or name:\n${help}`, active ? active.id : "");
    if (raw === null) return null;
    const value = String(raw || "").trim().toLowerCase();
    if (!value) return null;
    const match = projects.find((entry) => entry.id.toLowerCase() === value || entry.name.toLowerCase() === value);
    if (!match) {
      window.alert("Project not found. Try again with a listed project id or name.");
      return null;
    }
    return match.id;
  }

  function prepareListActionPayload(action, payload) {
    if (!action || typeof action !== "object") return payload;
    const next = payload && typeof payload === "object" ? { ...payload } : {};
    if (isDestructiveAction(action)) {
      const label = typeof action.label === "string" && action.label.trim() ? action.label.trim() : "Delete item";
      const confirmed = window.confirm(`${label}? This cannot be undone.`);
      if (!confirmed) return null;
    }
    if (isMoveToProjectAction(action)) {
      const projectId = promptProjectDestination();
      if (!projectId) return null;
      next.project_id = projectId;
      next.target_project_id = projectId;
    }
    return next;
  }

  async function dispatchListAction(action, payload, target, execute) {
    if (!action || typeof action !== "object" || typeof execute !== "function") return;
    if (isRenameAction(action)) {
      const title = resolveRenameTitle(payload);
      const initialValue = resolveRenameValue(payload);
      const completed = await openRenameModal({
        title,
        initialValue,
        onSave: async (nextValue) => {
          const renamePayload = withRenameFields(payload, nextValue);
          await execute(renamePayload);
        },
      });
      if (!completed) return;
      return;
    }
    const preparedPayload = prepareListActionPayload(action, payload);
    if (!preparedPayload) return;
    const opensUploadPicker = isUploadPickerAction(action);
    if (opensUploadPicker) {
      const postAction = {
        id: action.id,
        type: action.type,
        payload: preparedPayload,
      };
      const opened = openUploadPickerFromActionTarget(target, { postAction: postAction });
      if (!opened) {
        await execute(preparedPayload, target);
      }
      return;
    }
    await execute(preparedPayload, target);
  }

  function createListActionMenu(actions, runAction) {
    const menuWrap = document.createElement("div");
    menuWrap.className = "ui-list-actions ui-list-actions-menu";
    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "btn small ghost ui-list-menu-trigger";
    if (typeof root.createIconNode === "function") {
      const icon = root.createIconNode("more_horiz", { size: "small", decorative: true });
      icon.classList.add("ui-list-menu-trigger-icon");
      trigger.appendChild(icon);
    } else {
      trigger.textContent = "...";
    }
    trigger.setAttribute("aria-label", "Open actions");
    const menu = document.createElement("div");
    menu.className = "ui-list-menu hidden";
    let insertedDangerDivider = false;
    actions.forEach((action) => {
      if (!insertedDangerDivider && isDestructiveAction(action)) {
        const divider = document.createElement("div");
        divider.className = "ui-list-menu-divider";
        menu.appendChild(divider);
        insertedDangerDivider = true;
      }
      const item = document.createElement("button");
      item.type = "button";
      item.className = "ui-list-menu-item";
      if (isDestructiveAction(action)) {
        item.classList.add("destructive");
      }
      item.textContent = action.label || "Run";
      item.onclick = async (event) => {
        event.preventDefault();
        event.stopPropagation();
        menu.classList.add("hidden");
        await runAction(action, event.currentTarget);
      };
      menu.appendChild(item);
    });

    let outsideClickHandler = null;
    const closeMenu = () => {
      menu.classList.add("hidden");
      menuWrap.dataset.open = "false";
      if (outsideClickHandler) {
        document.removeEventListener("click", outsideClickHandler, true);
        outsideClickHandler = null;
      }
    };

    trigger.onclick = (event) => {
      event.preventDefault();
      event.stopPropagation();
      const isOpen = menuWrap.dataset.open === "true";
      if (isOpen) {
        closeMenu();
        return;
      }
      menu.classList.remove("hidden");
      menuWrap.dataset.open = "true";
      outsideClickHandler = (outsideEvent) => {
        if (!menuWrap.contains(outsideEvent.target)) {
          closeMenu();
        }
      };
      window.setTimeout(() => {
        if (outsideClickHandler) {
          document.addEventListener("click", outsideClickHandler, true);
        }
      }, 0);
    };

    menuWrap.appendChild(trigger);
    menuWrap.appendChild(menu);
    return menuWrap;
  }

  function renderListElement(el, handleAction) {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-element";
    const listWrap = document.createElement("div");
    listWrap.className = "ui-list";
    const rows = (Array.isArray(el.rows) ? el.rows : []).filter((row) => row && typeof row === "object");
    if (typeof el.record === "string" && el.record.trim()) {
      const registry = root.__listRowsByRecord || (root.__listRowsByRecord = {});
      registry[el.record.trim()] = rows.map((row) => ({ ...row }));
    }
    const mapping = el.item || {};
    const variant = el.variant || "two_line";
    const isIconVariant = variant === "icon" || variant === "icon_plain";
    if (variant === "icon_plain") {
      wrapper.classList.add("ui-list-plain-wrapper");
    }
    const actions = Array.isArray(el.actions) ? el.actions : [];
    const inlineRowAction = variant === "icon_plain" && actions.length === 1 ? actions[0] : null;
    const selectionMode = el.selection || "none";
    const idField = el.id_field || (rows[0] && (rows[0].id != null ? "id" : rows[0]._id != null ? "_id" : null));
    const selectedIds = new Set();
    const rowMap = new Map();
    const suggestionAction = resolveSuggestionAction(el);
    const groupByField = typeof el.group_by === "string" && el.group_by.trim() ? el.group_by.trim() : "";
    const groupLabelField = typeof el.group_label === "string" && el.group_label.trim() ? el.group_label.trim() : "";

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

    const groupedRows = [];
    if (groupByField) {
      const groupsByKey = new Map();
      rows.forEach((row) => {
        const keyText = formatListValue(row[groupByField]);
        const key = typeof keyText === "string" && keyText.trim() ? keyText.trim() : "Ungrouped";
        const labelText = groupLabelField ? formatListValue(row[groupLabelField]) : "";
        const label = typeof labelText === "string" && labelText.trim() ? labelText.trim() : key;
        if (!groupsByKey.has(key)) {
          groupsByKey.set(key, { key: key, label: label, rows: [] });
        }
        groupsByKey.get(key).rows.push(row);
      });
      groupsByKey.forEach((group) => groupedRows.push(group));
    } else {
      groupedRows.push({ key: "", label: "", rows: rows });
    }

    groupedRows.forEach((group) => {
      if (groupByField) {
        const groupNode = document.createElement("div");
        groupNode.className = "ui-list-group";
        const title = document.createElement("div");
        title.className = "ui-list-group-title";
        title.textContent = group.label || group.key || "Group";
        groupNode.appendChild(title);
        listWrap.appendChild(groupNode);
      }

      const groupHost = groupByField ? listWrap.lastElementChild : listWrap;
      const rowList = Array.isArray(group.rows) ? group.rows : [];
      rowList.forEach((row) => {
      const rowId = idField ? row[idField] : null;
      const item = document.createElement("div");
      item.className = `ui-list-item ui-list-${variant}`;
      if (row && row.active === true) {
        item.classList.add("active");
      }
      const citationEntry = citationEntryFromRow(row, mapping);
      const actionPayload = () => {
        const payload = {
          record: el.record,
          record_id: rowId,
          row: { ...row },
        };
        if (selectionMode !== "none") {
          payload.selection = {
            mode: selectionMode,
            ids: Array.from(selectedIds),
          };
        }
        return payload;
      };
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
      if (isIconVariant && mapping.icon) {
        const iconWrap = document.createElement("div");
        iconWrap.className = "ui-list-icon";
        const iconNode = createListIconNode(row[mapping.icon]);
        if (mapping.icon_color) {
          const iconColor = formatListValue(row[mapping.icon_color]).trim();
          if (iconColor) {
            iconNode.style.color = iconColor;
          }
        }
        iconWrap.appendChild(iconNode);
        content.appendChild(iconWrap);
      }
      const text = document.createElement("div");
      text.className = "ui-list-text";
      const primaryField = mapping.primary || idField;
      const primaryValue = primaryField ? row[primaryField] : rowId;
      const primaryTextValue = formatListValue(primaryValue);
      const primary = document.createElement("div");
      primary.className = "ui-list-primary";
      primary.textContent = primaryTextValue;
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

      if (actions.length && !inlineRowAction) {
        const runAction = async (action, target) => {
          const payload = actionPayload();
          await dispatchListAction(action, payload, target, async (preparedPayload) => {
            await handleAction(action, preparedPayload, target);
          });
        };
        const actionsWrap =
          actions.length > 1 ? createListActionMenu(actions, runAction) : document.createElement("div");
        if (actions.length === 1) {
          actionsWrap.className = "ui-list-actions";
          const action = actions[0];
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "btn small";
          btn.textContent = action.label || "Run";
          btn.onclick = async (e) => {
            await runAction(action, e.currentTarget);
          };
          actionsWrap.appendChild(btn);
        }
        item.appendChild(actionsWrap);
      }

      if (inlineRowAction && !citationEntry && !suggestionAction) {
        item.classList.add("ui-list-row-action");
        item.tabIndex = 0;
        item.setAttribute("role", "button");
        const runInlineAction = () => {
          if (selectionMode === "single" && rowId != null) {
            selectedIds.clear();
            selectedIds.add(rowId);
            rowMap.forEach((node, id) => node.classList.toggle("selected", id === rowId));
          }
          handleAction(inlineRowAction, actionPayload(), item);
        };
        item.addEventListener("click", (event) => {
          if (interactiveListTarget(event.target)) return;
          runInlineAction();
        });
        item.addEventListener("keydown", (event) => {
          if (event.key !== "Enter" && event.key !== " ") return;
          event.preventDefault();
          runInlineAction();
        });
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
      groupHost.appendChild(item);
    });
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
