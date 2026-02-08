(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});

  function renderCitationChipsElement(el) {
    const wrapper = document.createElement("div");
    wrapper.className = `ui-citation-chips${el && el.compact ? " compact" : ""}`;
    const citations = normalizeCitations(el && el.citations);
    if (!citations.length) {
      const empty = document.createElement("span");
      empty.className = "ui-citation-chips-empty";
      empty.textContent = "No sources";
      wrapper.appendChild(empty);
      return wrapper;
    }
    citations.forEach((entry) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "ui-citation-chip";
      button.textContent = `[${entry.index}]`;
      button.title = entry.title || "Source";
      button.setAttribute("aria-label", `Open source ${entry.index}: ${entry.title || "Source"}`);
      button.onclick = () => openCitation(entry, button);
      wrapper.appendChild(button);
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
      openCitation(toCitationEntry(el), previewButton);
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
    badge.className = `ui-trust-indicator ui-trust-${trust.tone}${el && el.compact ? " compact" : ""}`;
    badge.textContent = trust.label;
    badge.title = trust.title;
    badge.setAttribute("role", "status");
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
    if (typeof root.normalizeCitationEntries === "function") return root.normalizeCitationEntries(raw);
    if (!Array.isArray(raw)) return [];
    return raw
      .filter((entry) => entry && typeof entry === "object")
      .map((entry, idx) => ({
        index:
          typeof entry.index === "number" && Number.isFinite(entry.index)
            ? Math.max(1, Math.trunc(entry.index))
            : idx + 1,
        title: typeof entry.title === "string" && entry.title.trim() ? entry.title.trim() : "Source",
        url: typeof entry.url === "string" ? entry.url : undefined,
        source_id: typeof entry.source_id === "string" ? entry.source_id : undefined,
        snippet: typeof entry.snippet === "string" ? entry.snippet : undefined,
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
    const entry = {
      title: (el && el.title) || "Source",
      snippet: el && el.snippet,
      source_id: el && el.source_id,
      url: el && el.url,
      chunk_id: el && el.chunk_id,
      document_id: el && el.document_id,
      page: el && el.page,
      page_number: el && el.page_number,
    };
    return entry;
  }

  function openCitation(entry, opener) {
    if (typeof root.openCitationPreview === "function") {
      root.openCitationPreview(entry, opener);
      return;
    }
    if (entry && typeof entry.url === "string" && entry.url.trim()) {
      window.open(entry.url, "_blank", "noopener,noreferrer");
    }
  }

  function normalizeTrustValue(value) {
    if (typeof value === "boolean") {
      if (value) {
        return { tone: "high", label: "Trusted", title: "Answer is fully grounded." };
      }
      return { tone: "low", label: "Needs review", title: "Answer may not be fully grounded." };
    }
    if (typeof value === "number" && Number.isFinite(value)) {
      const clamped = Math.max(0, Math.min(1, value));
      const percent = Math.round(clamped * 100);
      if (clamped >= 0.8) return { tone: "high", label: `Trust ${percent}%`, title: "High grounding confidence." };
      if (clamped >= 0.5) return { tone: "medium", label: `Trust ${percent}%`, title: "Moderate grounding confidence." };
      return { tone: "low", label: `Trust ${percent}%`, title: "Low grounding confidence." };
    }
    return { tone: "medium", label: "Trust unknown", title: "No trust value available." };
  }

  root.renderCitationChipsElement = renderCitationChipsElement;
  root.renderSourcePreviewElement = renderSourcePreviewElement;
  root.renderTrustIndicatorElement = renderTrustIndicatorElement;
  root.renderScopeSelectorElement = renderScopeSelectorElement;
})();
