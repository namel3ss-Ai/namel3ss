(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});

  function renderCitationChipsElement(el) {
    const wrapper = document.createElement("div");
    wrapper.className = `ui-citation-chips${el && el.compact ? " compact" : ""}`;
    const citations = normalizeCitations(el && el.citations);
    if (!citations.length) {
      wrapper.dataset.empty = "true";
      wrapper.hidden = true;
      return wrapper;
    }
    if (el && el.enhanced === false) {
      return renderLegacyCitations(citations, { compact: Boolean(el.compact) });
    }
    citations.forEach((entry) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "ui-citation-chip";
      button.textContent = `[${entry.index}]`;
      button.title = entry.title || "Source";
      button.setAttribute("aria-label", `Open source ${entry.index}: ${entry.title || "Source"}`);
      if (typeof entry.citation_id === "string" && entry.citation_id) {
        button.dataset.citationId = entry.citation_id;
      }
      button.onclick = () => openCitation(entry, button, citations);
      wrapper.appendChild(button);
    });
    return wrapper;
  }

  function renderLegacyCitations(citations, options) {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-citation-legacy";
    if (options && options.compact) {
      wrapper.classList.add("compact");
    }
    citations.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "ui-citation-legacy-row";
      const title = document.createElement("button");
      title.type = "button";
      title.className = "ui-citation-legacy-link";
      title.textContent = `${entry.index}. ${entry.title || "Source"}`;
      if (typeof entry.citation_id === "string" && entry.citation_id) {
        row.dataset.citationId = entry.citation_id;
      }
      title.onclick = () => openCitation(entry, title, citations);
      row.appendChild(title);
      if (entry.snippet) {
        const snippet = document.createElement("div");
        snippet.className = "ui-citation-legacy-snippet";
        snippet.textContent = entry.snippet;
        row.appendChild(snippet);
      }
      wrapper.appendChild(row);
    });
    return wrapper;
  }

  function renderSourcePreviewElement(el) {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-source-preview";

    const title = document.createElement("div");
    title.className = "ui-source-preview-title";
    title.textContent = el && el.title ? String(el.title) : "Source preview";
    wrapper.appendChild(title);

    const meta = document.createElement("div");
    meta.className = "ui-source-preview-meta";
    meta.textContent = sourceMetaText(el);
    wrapper.appendChild(meta);

    const snippet = document.createElement("div");
    snippet.className = "ui-source-preview-snippet";
    snippet.textContent = el && typeof el.snippet === "string" && el.snippet.trim() ? el.snippet : "No preview text.";
    wrapper.appendChild(snippet);

    const actions = document.createElement("div");
    actions.className = "ui-source-preview-actions";
    const previewButton = document.createElement("button");
    previewButton.type = "button";
    previewButton.className = "btn small ghost";
    previewButton.textContent = "Open preview";
    previewButton.onclick = () => {
      openCitation(toCitationEntry(el), previewButton, [toCitationEntry(el)]);
    };
    actions.appendChild(previewButton);
    if (el && typeof el.url === "string" && el.url.trim()) {
      const link = document.createElement("a");
      link.href = el.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.className = "btn small ghost";
      link.textContent = "View full document";
      actions.appendChild(link);
    }
    wrapper.appendChild(actions);

    if (el && typeof el.error === "string" && el.error.trim()) {
      const error = document.createElement("div");
      error.className = "ui-source-preview-error";
      error.textContent = el.error;
      wrapper.appendChild(error);
    }
    return wrapper;
  }

  function renderTrustIndicatorElement(el) {
    const value = el ? el.value : null;
    const trust = normalizeTrustValue(value);
    const badge = document.createElement("span");
    badge.className = `ui-trust-indicator${el && el.compact ? " compact" : ""}`;
    badge.setAttribute("role", "status");
    if (!trust) {
      badge.classList.add("hidden");
      badge.setAttribute("aria-hidden", "true");
      badge.textContent = "";
      return badge;
    }
    badge.classList.add(`ui-trust-${trust.tone}`);
    badge.textContent = trust.label;
    badge.title = trust.title;
    badge.setAttribute("aria-label", trust.title);
    return badge;
  }

  function renderScopeSelectorElement(el, handleAction) {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-scope-selector";
    const actionType = el && typeof el.action_type === "string" && el.action_type ? el.action_type : "scope_select";
    const selectionMode = el && el.selection === "single" ? "single" : "multi";
    const studioRoot = window.N3Studio || {};
    const run = studioRoot && studioRoot.run ? studioRoot.run : null;
    const isChatThreadSelector = actionType === "chat.thread.select";
    const title = document.createElement("div");
    title.className = "ui-scope-selector-title";
    title.textContent = el && typeof el.title === "string" && el.title ? el.title : "Retrieval scope";
    wrapper.appendChild(title);

    const options = Array.isArray(el && el.options) ? el.options : [];
    const list = document.createElement("div");
    list.className = "ui-scope-selector-options";
    wrapper.appendChild(list);

    const selected = new Set(Array.isArray(el && el.active) ? el.active.map(String) : []);
    const buttons = [];
    const buttonById = new Map();
    let emptyState = null;

    const applySelection = () => {
      buttons.forEach((entry) => {
        const isActive = selected.has(entry.id);
        entry.button.classList.toggle("active", isActive);
        entry.button.setAttribute("aria-pressed", isActive ? "true" : "false");
      });
    };

    const syncEmptyState = () => {
      if (buttons.length) {
        if (emptyState) {
          emptyState.remove();
          emptyState = null;
        }
        return;
      }
      if (!emptyState) {
        emptyState = document.createElement("div");
        emptyState.className = "ui-scope-selector-empty";
        emptyState.textContent = "No scopes available.";
        list.appendChild(emptyState);
      }
    };

    const actionPayload = () => ({ active: Array.from(selected) });

    const dispatchSelectorAction = async (button) => {
      if (typeof handleAction !== "function" || !el || !el.action_id) {
        return { ok: true };
      }
      return handleAction(
        { id: el.action_id, type: actionType, target_state: el.active_source || "" },
        actionPayload(),
        button
      );
    };

    const runThreadRouteSelection = async (threadId, previousSelected) => {
      if (!run || typeof run.loadChatThread !== "function") {
        return dispatchSelectorAction(buttonById.get(threadId));
      }
      const previousThreadId = previousSelected.length ? String(previousSelected[0]) : "";
      if (previousThreadId && previousThreadId !== threadId && typeof run.saveChatThread === "function") {
        const saveResponse = await run.saveChatThread(previousThreadId, {}, {
          activate: false,
          refreshData: false,
          refreshUI: false,
        });
        if (saveResponse && saveResponse.ok === false) {
          const fallback = await dispatchSelectorAction(buttonById.get(threadId));
          return fallback || saveResponse;
        }
      }
      const loadResponse = await run.loadChatThread(threadId, {
        activate: true,
        refreshData: true,
        refreshUI: true,
      });
      if (loadResponse && loadResponse.ok === false) {
        const fallback = await dispatchSelectorAction(buttonById.get(threadId));
        return fallback || loadResponse;
      }
      return loadResponse || { ok: true };
    };

    const addOptionButton = (id, name, metadata) => {
      if (!id || buttonById.has(id)) return;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "ui-scope-option";
      button.textContent = scopeOptionLabel(name || id, metadata);
      const tooltip = scopeOptionTooltip(metadata);
      if (tooltip) {
        button.title = tooltip;
      }
      button.onclick = async () => {
        const previous = Array.from(selected);
        if (selectionMode === "single") {
          selected.clear();
          selected.add(id);
        } else if (selected.has(id)) {
          selected.delete(id);
        } else {
          selected.add(id);
        }
        applySelection();
        const response = isChatThreadSelector
          ? await runThreadRouteSelection(id, previous)
          : await dispatchSelectorAction(button);
        if (response && response.ok === false) {
          selected.clear();
          previous.forEach((entry) => selected.add(entry));
          applySelection();
        }
      };
      list.appendChild(button);
      buttons.push({ id: id, button: button });
      buttonById.set(id, button);
      syncEmptyState();
    };

    options.forEach((option) => {
      if (!option || typeof option !== "object") return;
      const id = typeof option.id === "string" ? option.id : "";
      const name = typeof option.name === "string" ? option.name : id;
      if (!id) return;
      addOptionButton(id, name, null);
    });
    syncEmptyState();

    if (isChatThreadSelector && run && typeof run.listChatThreads === "function") {
      run
        .listChatThreads()
        .then((response) => {
          const chat = response && typeof response === "object" ? response.chat : null;
          const rows = Array.isArray(chat && chat.threads) ? chat.threads : [];
          rows.forEach((row) => {
            if (!row || typeof row !== "object") return;
            const id = typeof row.id === "string" ? row.id : "";
            if (!id) return;
            const label = typeof row.name === "string" && row.name ? row.name : id;
            const metadata = {
              last_message_id: row.last_message_id,
              message_count: row.message_count,
            };
            if (buttonById.has(id)) {
              const button = buttonById.get(id);
              button.textContent = scopeOptionLabel(label, metadata);
              const tooltip = scopeOptionTooltip(metadata);
              if (tooltip) {
                button.title = tooltip;
              }
              return;
            }
            addOptionButton(id, label, metadata);
          });
          const explicitActive = chat && typeof chat.active_thread_id === "string" ? chat.active_thread_id : "";
          const rowActive = rows.find((row) => row && row.active === true);
          const nextActive = explicitActive || (rowActive && typeof rowActive.id === "string" ? rowActive.id : "");
          if (nextActive) {
            selected.clear();
            selected.add(nextActive);
            applySelection();
          }
        })
        .catch(() => {});
    }

    applySelection();
    return wrapper;
  }

  function normalizeCitations(raw) {
    if (typeof root.normalizeCitationEntries === "function") {
      const normalized = root.normalizeCitationEntries(raw);
      return normalized.map((entry, idx) => ({
        citation_id:
          typeof entry.citation_id === "string" && entry.citation_id.trim()
            ? entry.citation_id.trim()
            : `citation.${idx + 1}`,
        ...entry,
      }));
    }
    if (!Array.isArray(raw)) return [];
    return raw
      .filter((entry) => entry && typeof entry === "object")
      .map((entry, idx) => ({
        citation_id:
          typeof entry.citation_id === "string" && entry.citation_id.trim()
            ? entry.citation_id.trim()
            : `citation.${idx + 1}`,
        index:
          typeof entry.index === "number" && Number.isFinite(entry.index)
            ? Math.max(1, Math.trunc(entry.index))
            : idx + 1,
        title: typeof entry.title === "string" && entry.title.trim() ? entry.title.trim() : "Source",
        url: typeof entry.url === "string" ? entry.url : undefined,
        source_id: typeof entry.source_id === "string" ? entry.source_id : undefined,
        snippet: typeof entry.snippet === "string" ? entry.snippet : undefined,
        chunk_id: typeof entry.chunk_id === "string" ? entry.chunk_id : undefined,
        document_id: typeof entry.document_id === "string" ? entry.document_id : undefined,
        highlight_color: typeof entry.highlight_color === "string" ? entry.highlight_color : undefined,
        page: typeof entry.page === "number" || typeof entry.page === "string" ? entry.page : undefined,
        page_number:
          typeof entry.page_number === "number" || typeof entry.page_number === "string" ? entry.page_number : undefined,
      }));
  }

  function scopeOptionLabel(label, metadata) {
    const base = typeof label === "string" ? label : "";
    if (!metadata || typeof metadata !== "object") return base;
    const messageCount = Number(metadata.message_count);
    if (!Number.isFinite(messageCount) || messageCount < 0) return base;
    const count = Math.trunc(messageCount);
    const noun = count === 1 ? "msg" : "msgs";
    return `${base} (${count} ${noun})`;
  }

  function scopeOptionTooltip(metadata) {
    if (!metadata || typeof metadata !== "object") return "";
    const labels = [];
    const messageCount = Number(metadata.message_count);
    if (Number.isFinite(messageCount) && messageCount >= 0) {
      const count = Math.trunc(messageCount);
      const noun = count === 1 ? "message" : "messages";
      labels.push(`${count} ${noun}`);
    }
    const lastMessageId =
      typeof metadata.last_message_id === "string" && metadata.last_message_id.trim()
        ? metadata.last_message_id.trim()
        : "";
    if (lastMessageId) {
      labels.push(`last: ${lastMessageId}`);
    }
    return labels.join(" | ");
  }

  function sourceMetaText(el) {
    if (!el || typeof el !== "object") return "Unavailable";
    if (typeof el.source_id === "string" && el.source_id) return `Source id: ${el.source_id}`;
    if (typeof el.url === "string" && el.url) return el.url;
    if (typeof el.source === "string" && el.source) return el.source;
    return "Unavailable";
  }

  function toCitationEntry(el) {
    return {
      citation_id: el && typeof el.citation_id === "string" ? el.citation_id : undefined,
      title: (el && el.title) || "Source",
      snippet: el && el.snippet,
      source_id: el && el.source_id,
      url: el && el.url,
      chunk_id: el && el.chunk_id,
      document_id: el && el.document_id,
      highlight_color: el && el.highlight_color,
      page: el && el.page,
      page_number: el && el.page_number,
    };
  }

  function openCitation(entry, opener, citationSet) {
    const citations = Array.isArray(citationSet) ? citationSet : undefined;
    if (entry && typeof entry.citation_id === "string" && entry.citation_id && typeof root.selectCitationId === "function") {
      root.selectCitationId(entry.citation_id);
    }
    if (typeof root.focusCitationInDrawer === "function") {
      root.focusCitationInDrawer(entry);
    }
    if (typeof root.openCitationPreview === "function") {
      root.openCitationPreview(entry, opener, citations);
      return;
    }
    if (entry && typeof entry.url === "string" && entry.url.trim()) {
      window.open(entry.url, "_blank", "noopener,noreferrer");
    }
  }

  function normalizeTrustValue(value) {
    if (value === true) {
      return { tone: "high", label: "Grounded", title: "Grounded by cited sources." };
    }
    if (value === false) {
      return { tone: "low", label: "No sources", title: "No supporting sources were available." };
    }
    if (typeof value === "number" && Number.isFinite(value)) {
      const clamped = Math.max(0, Math.min(1, value));
      if (clamped >= 0.75) {
        return { tone: "high", label: "Grounded", title: "Grounded by cited sources." };
      }
      if (clamped > 0) {
        return { tone: "medium", label: "Partial", title: "Partially grounded answer." };
      }
      return { tone: "low", label: "No sources", title: "No supporting sources were available." };
    }
    if (typeof value === "string") {
      const normalized = value.trim().toLowerCase();
      if (normalized === "grounded") {
        return { tone: "high", label: "Grounded", title: "Grounded by cited sources." };
      }
      if (normalized === "partial") {
        return { tone: "medium", label: "Partial", title: "Partially grounded answer." };
      }
      if (normalized === "no_sources" || normalized === "no sources") {
        return { tone: "low", label: "No sources", title: "No supporting sources were available." };
      }
    }
    return null;
  }

  root.renderCitationChipsElement = renderCitationChipsElement;
  root.renderSourcePreviewElement = renderSourcePreviewElement;
  root.renderTrustIndicatorElement = renderTrustIndicatorElement;
  root.renderScopeSelectorElement = renderScopeSelectorElement;
  root.normalizeRagConfidenceValue = normalizeTrustValue;
})();
