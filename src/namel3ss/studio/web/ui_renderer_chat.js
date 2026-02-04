(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});
  const previewState = {
    container: null,
    panel: null,
    title: null,
    meta: null,
    snippet: null,
    pageText: null,
    pageLabel: null,
    prevButton: null,
    nextButton: null,
    frame: null,
    error: null,
    returnFocus: null,
    documentId: null,
    pageNumber: null,
    pageCount: null,
    entrySnippet: null,
  };

  function renderChatElement(el, handleAction) {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-element ui-chat";

    const children = Array.isArray(el.children) ? el.children : [];
    children.forEach((child) => {
      const node = renderChatChild(child, handleAction);
      if (node) wrapper.appendChild(node);
    });

    return wrapper;
  }

  function renderChatChild(child, handleAction) {
    if (!child || !child.type) return null;
    if (child.type === "messages") return renderMessages(child);
    if (child.type === "composer") return renderComposer(child, handleAction);
    if (child.type === "thinking") return renderThinking(child);
    if (child.type === "citations") return renderCitations(child);
    if (child.type === "memory") return renderMemory(child);
    return null;
  }

  function renderMessages(child) {
    const container = document.createElement("div");
    container.className = "ui-chat-messages";
    const messages = Array.isArray(child.messages) ? child.messages : [];
    if (!messages.length) {
      const empty = document.createElement("div");
      empty.className = "ui-chat-empty";
      empty.textContent = "No messages yet.";
      container.appendChild(empty);
      return container;
    }
    messages.forEach((message) => {
      const row = document.createElement("div");
      row.className = "ui-chat-message";
      const role = document.createElement("div");
      role.className = "ui-chat-role";
      role.textContent = message.role || "user";
      const content = document.createElement("div");
      content.className = "ui-chat-content";
      content.textContent = message.content || "";
      row.appendChild(role);
      row.appendChild(content);
      if (message.created) {
        const created = document.createElement("div");
        created.className = "ui-chat-created";
        created.textContent = String(message.created);
        row.appendChild(created);
      }
      container.appendChild(row);
    });
    return container;
  }

  function renderComposer(child, handleAction) {
    const form = document.createElement("form");
    form.className = "ui-chat-composer";
    const fields = normalizeComposerFields(child);
    const inputs = new Map();
    fields.forEach((field) => {
      const input = document.createElement("input");
      input.type = "text";
      const name = field.name || "message";
      const placeholder = name === "message" ? "Type a message" : String(name);
      input.placeholder = placeholder;
      input.setAttribute("aria-label", placeholder);
      inputs.set(name, input);
      form.appendChild(input);
    });
    const button = document.createElement("button");
    button.type = "submit";
    button.className = "btn small";
    button.textContent = "Send";
    form.appendChild(button);

    form.onsubmit = async (e) => {
      e.preventDefault();
      const payload = {};
      fields.forEach((field) => {
        const name = field.name || "message";
        const input = inputs.get(name);
        payload[name] = input ? input.value || "" : "";
      });
      inputs.forEach((input) => {
        if (input) input.value = "";
      });
      await handleAction(
        { id: child.action_id, type: "call_flow", flow: child.flow },
        payload,
        button
      );
    };
    return form;
  }

  function resolveCitationTarget(entry) {
    if (!entry) return null;
    const docId =
      textValue(entry.document_id) ||
      textValue(entry.documentId) ||
      textValue(entry.upload_id) ||
      null;
    const pageNumber = toPageNumber(entry.page_number || entry.page);
    if (docId && pageNumber) return { documentId: docId, pageNumber: pageNumber };
    const chunkId = textValue(entry.chunk_id) || textValue(entry.source_id);
    if (chunkId && pageNumber) {
      const parts = chunkId.split(":");
      if (parts.length > 1 && parts[0]) {
        return { documentId: parts[0], pageNumber: pageNumber };
      }
    }
    return null;
  }

  function textValue(value) {
    if (typeof value !== "string") return "";
    const trimmed = value.trim();
    return trimmed ? trimmed : "";
  }

  function toPageNumber(value) {
    if (typeof value === "number" && Number.isFinite(value)) {
      return Math.trunc(value);
    }
    if (typeof value === "string" && value.trim()) {
      const trimmed = value.trim();
      if (/^\d+$/.test(trimmed)) {
        const parsed = Number.parseInt(trimmed, 10);
        if (!Number.isNaN(parsed)) return parsed;
      }
    }
    return null;
  }

  function ensureCitationPreview() {
    if (previewState.container) return previewState;
    const overlay = document.createElement("div");
    overlay.className = "ui-overlay ui-drawer hidden ui-citation-preview";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-hidden", "true");
    overlay.setAttribute("aria-modal", "true");
    const panel = document.createElement("div");
    panel.className = "ui-overlay-panel ui-citation-preview-panel";
    panel.tabIndex = -1;
    const header = document.createElement("div");
    header.className = "ui-overlay-header";
    const title = document.createElement("div");
    title.className = "ui-overlay-title";
    title.textContent = "Source preview";
    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "btn small ghost";
    closeBtn.textContent = "Close";
    closeBtn.setAttribute("aria-label", "Close preview");
    closeBtn.onclick = () => closeCitationPreview();
    header.appendChild(title);
    header.appendChild(closeBtn);
    panel.appendChild(header);

    const meta = document.createElement("div");
    meta.className = "ui-citation-preview-meta";
    panel.appendChild(meta);

    const snippetSection = document.createElement("div");
    snippetSection.className = "ui-citation-preview-section";
    const snippetLabel = document.createElement("div");
    snippetLabel.className = "ui-citation-preview-label";
    snippetLabel.textContent = "Snippet";
    const snippet = document.createElement("div");
    snippet.className = "ui-citation-preview-snippet";
    snippetSection.appendChild(snippetLabel);
    snippetSection.appendChild(snippet);
    panel.appendChild(snippetSection);

    const textSection = document.createElement("div");
    textSection.className = "ui-citation-preview-section";
    const textLabel = document.createElement("div");
    textLabel.className = "ui-citation-preview-label";
    textLabel.textContent = "Page text";
    const pageText = document.createElement("div");
    pageText.className = "ui-citation-preview-text";
    textSection.appendChild(textLabel);
    textSection.appendChild(pageText);
    panel.appendChild(textSection);

    const controls = document.createElement("div");
    controls.className = "ui-citation-preview-controls";
    const prevBtn = document.createElement("button");
    prevBtn.type = "button";
    prevBtn.className = "btn small ghost";
    prevBtn.textContent = "Prev";
    const pageLabel = document.createElement("div");
    pageLabel.className = "ui-citation-preview-page";
    const nextBtn = document.createElement("button");
    nextBtn.type = "button";
    nextBtn.className = "btn small ghost";
    nextBtn.textContent = "Next";
    controls.appendChild(prevBtn);
    controls.appendChild(pageLabel);
    controls.appendChild(nextBtn);
    panel.appendChild(controls);

    const frame = document.createElement("iframe");
    frame.className = "ui-citation-preview-frame";
    frame.title = "Document preview";
    panel.appendChild(frame);

    const error = document.createElement("div");
    error.className = "ui-citation-preview-error";
    panel.appendChild(error);

    overlay.appendChild(panel);
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) closeCitationPreview();
    });
    overlay.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeCitationPreview();
    });
    document.body.appendChild(overlay);

    previewState.container = overlay;
    previewState.panel = panel;
    previewState.title = title;
    previewState.meta = meta;
    previewState.snippet = snippet;
    previewState.pageText = pageText;
    previewState.pageLabel = pageLabel;
    previewState.prevButton = prevBtn;
    previewState.nextButton = nextBtn;
    previewState.frame = frame;
    previewState.error = error;

    prevBtn.onclick = () => navigatePreviewPage(-1);
    nextBtn.onclick = () => navigatePreviewPage(1);

    return previewState;
  }

  function openCitationPreview(entry, opener) {
    const target = resolveCitationTarget(entry);
    if (!target) return;
    const preview = ensureCitationPreview();
    preview.returnFocus = opener || document.activeElement;
    preview.entrySnippet = typeof entry.snippet === "string" ? entry.snippet : "";
    preview.title.textContent = entry.title || "Source";
    preview.container.classList.remove("hidden");
    preview.container.setAttribute("aria-hidden", "false");
    preview.panel.focus();
    loadPreviewPage(target.documentId, target.pageNumber);
  }

  function closeCitationPreview() {
    const preview = previewState;
    if (!preview.container) return;
    preview.container.classList.add("hidden");
    preview.container.setAttribute("aria-hidden", "true");
    preview.documentId = null;
    preview.pageNumber = null;
    preview.pageCount = null;
    preview.entrySnippet = null;
    if (preview.returnFocus && preview.returnFocus.focus) {
      preview.returnFocus.focus();
    }
    preview.returnFocus = null;
  }

  function navigatePreviewPage(delta) {
    const preview = previewState;
    if (!preview.documentId || !preview.pageNumber || !preview.pageCount) return;
    const nextPage = preview.pageNumber + delta;
    if (nextPage < 1 || nextPage > preview.pageCount) return;
    loadPreviewPage(preview.documentId, nextPage);
  }

  async function loadPreviewPage(documentId, pageNumber) {
    const preview = ensureCitationPreview();
    preview.documentId = documentId;
    preview.pageNumber = pageNumber;
    preview.meta.textContent = "Loading page...";
    preview.error.textContent = "";
    preview.pageLabel.textContent = "";
    preview.prevButton.disabled = true;
    preview.nextButton.disabled = true;
    preview.pageText.textContent = "";
    preview.snippet.textContent = "Loading snippet...";
    preview.frame.removeAttribute("src");

    try {
      const url = `/api/documents/${encodeURIComponent(documentId)}/pages/${pageNumber}`;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Preview request failed (${response.status})`);
      }
      const payload = await response.json();
      if (!payload || payload.ok !== true) {
        throw new Error("Preview response was not ok.");
      }
      const doc = payload.document || {};
      const page = payload.page || {};
      const pageCount = Number(doc.page_count) || pageNumber;
      preview.pageCount = pageCount;
      preview.pageNumber = Number(page.number) || pageNumber;
      preview.pageLabel.textContent = `Page ${preview.pageNumber} of ${pageCount}`;
      const name = doc.source_name || preview.title.textContent || "Document";
      preview.meta.textContent = `${name} · ${preview.pageLabel.textContent}`;
      preview.prevButton.disabled = preview.pageNumber <= 1;
      preview.nextButton.disabled = preview.pageNumber >= pageCount;
      preview.frame.src = payload.pdf_url || `/api/documents/${encodeURIComponent(documentId)}/pdf#page=${preview.pageNumber}`;
      const pageText = typeof page.text === "string" ? page.text : "";
      preview.pageText.textContent = pageText || "No extracted text for this page.";
      preview.snippet.textContent = formatSnippet(preview.entrySnippet, pageText);
    } catch (err) {
      preview.error.textContent = err && err.message ? err.message : "Unable to load preview.";
      preview.meta.textContent = "Preview unavailable";
      preview.snippet.textContent = "No snippet available.";
    }
  }

  function formatSnippet(snippet, pageText) {
    const raw = typeof snippet === "string" && snippet.trim() ? snippet : pageText;
    if (!raw) return "No snippet available.";
    const trimmed = raw.trim();
    if (trimmed.length > 320) {
      return `${trimmed.slice(0, 320)}...`;
    }
    return trimmed;
  }

  function normalizeComposerFields(child) {
    const raw = Array.isArray(child.fields) ? child.fields : [];
    const fields = [];
    const seen = new Set();
    raw.forEach((field) => {
      if (!field || !field.name) return;
      const name = String(field.name);
      if (seen.has(name)) return;
      seen.add(name);
      fields.push({ name: name, type: field.type || "text" });
    });
    if (!fields.length) return [{ name: "message", type: "text" }];
    if (!seen.has("message")) fields.unshift({ name: "message", type: "text" });
    return fields;
  }

  function renderThinking(child) {
    const indicator = document.createElement("div");
    indicator.className = "ui-chat-thinking";
    indicator.textContent = "Thinking...";
    indicator.hidden = !child.active;
    return indicator;
  }

  function renderCitations(child) {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-chat-citations";
    const title = document.createElement("div");
    title.className = "ui-chat-citations-title";
    title.textContent = "Citations";
    wrapper.appendChild(title);
    const citations = Array.isArray(child.citations) ? child.citations : [];
    if (!citations.length) {
      const empty = document.createElement("div");
      empty.className = "ui-chat-empty";
      empty.textContent = "No citations.";
      wrapper.appendChild(empty);
      return wrapper;
    }
    citations.forEach((entry) => {
      const item = document.createElement("div");
      item.className = "ui-chat-citation";
      const heading = document.createElement("div");
      heading.className = "ui-chat-citation-title";
      heading.textContent = entry.title || "Source";
      item.appendChild(heading);
      const target = resolveCitationTarget(entry);
      if (target && target.pageNumber) {
        const meta = document.createElement("div");
        meta.className = "ui-chat-citation-meta";
        meta.textContent = `Page ${target.pageNumber}`;
        item.appendChild(meta);
      }
      if (entry.url) {
        const link = document.createElement("a");
        link.href = entry.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = entry.url;
        item.appendChild(link);
      } else if (entry.source_id) {
        const sourceId = document.createElement("div");
        sourceId.className = "ui-chat-citation-source";
        sourceId.textContent = entry.source_id;
        item.appendChild(sourceId);
      }
      if (target) {
        const actions = document.createElement("div");
        actions.className = "ui-chat-citation-actions";
        const openBtn = document.createElement("button");
        openBtn.type = "button";
        openBtn.className = "btn small ghost";
        openBtn.textContent = "Open page";
        openBtn.onclick = (event) => {
          event.stopPropagation();
          openCitationPreview(entry, event.currentTarget);
        };
        actions.appendChild(openBtn);
        item.appendChild(actions);
      }
      if (entry.snippet) {
        const snippet = document.createElement("div");
        snippet.className = "ui-chat-citation-snippet";
        snippet.textContent = entry.snippet;
        item.appendChild(snippet);
      }
      wrapper.appendChild(item);
    });
    return wrapper;
  }

  function renderMemory(child) {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-chat-memory";
    const title = document.createElement("div");
    title.className = "ui-chat-memory-title";
    title.textContent = "Memory";
    wrapper.appendChild(title);
    if (child.lane) {
      const lane = document.createElement("div");
      lane.className = "ui-chat-memory-lane";
      lane.textContent = child.lane;
      wrapper.appendChild(lane);
    }
    const items = Array.isArray(child.items) ? child.items : [];
    if (!items.length) {
      const empty = document.createElement("div");
      empty.className = "ui-chat-empty";
      empty.textContent = "No memory items.";
      wrapper.appendChild(empty);
      return wrapper;
    }
    items.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "ui-chat-memory-item";
      const kind = document.createElement("div");
      kind.className = "ui-chat-memory-kind";
      kind.textContent = entry.kind || "note";
      const text = document.createElement("div");
      text.className = "ui-chat-memory-text";
      text.textContent = entry.text || "";
      row.appendChild(kind);
      row.appendChild(text);
      wrapper.appendChild(row);
    });
    return wrapper;
  }

  root.renderChatElement = renderChatElement;
})();
