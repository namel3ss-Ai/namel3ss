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
    const title = document.createElement("div");
    title.className = "ui-scope-selector-title";
    title.textContent = "Retrieval scope";
    wrapper.appendChild(title);

    const options = Array.isArray(el && el.options) ? el.options : [];
    const list = document.createElement("div");
    list.className = "ui-scope-selector-options";
    wrapper.appendChild(list);

    const selected = new Set(Array.isArray(el && el.active) ? el.active.map(String) : []);
    const buttons = [];

    const applySelection = () => {
      buttons.forEach((entry) => {
        const isActive = selected.has(entry.id);
        entry.button.classList.toggle("active", isActive);
        entry.button.setAttribute("aria-pressed", isActive ? "true" : "false");
      });
    };

    options.forEach((option) => {
      if (!option || typeof option !== "object") return;
      const id = typeof option.id === "string" ? option.id : "";
      const name = typeof option.name === "string" ? option.name : id;
      if (!id) return;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "ui-scope-option";
      button.textContent = name || id;
      button.onclick = async () => {
        if (selected.has(id)) selected.delete(id);
        else selected.add(id);
        applySelection();
        if (typeof handleAction !== "function" || !el || !el.action_id) return;
        const payload = { active: Array.from(selected) };
        const response = await handleAction(
          { id: el.action_id, type: "scope_select", target_state: el.active_source || "" },
          payload,
          button
        );
        if (response && response.ok === false) {
          if (selected.has(id)) selected.delete(id);
          else selected.add(id);
          applySelection();
        }
      };
      list.appendChild(button);
      buttons.push({ id: id, button: button });
    });

    if (!buttons.length) {
      const empty = document.createElement("div");
      empty.className = "ui-scope-selector-empty";
      empty.textContent = "No scopes available.";
      list.appendChild(empty);
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
        page: typeof entry.page === "number" || typeof entry.page === "string" ? entry.page : undefined,
        page_number:
          typeof entry.page_number === "number" || typeof entry.page_number === "string" ? entry.page_number : undefined,
      }));
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
