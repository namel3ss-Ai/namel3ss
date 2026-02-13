(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});
  const previewState = {
    container: null,
    panel: null,
    title: null,
    tabs: null,
    sourcesView: null,
    previewView: null,
    explainView: null,
    explainText: null,
    sourcesList: null,
    sourceItems: [],
    meta: null,
    snippet: null,
    pageText: null,
    pageNotice: null,
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
    chunkId: null,
    citationId: null,
    citations: [],
    selectedCitationIndex: -1,
    tabButtons: [],
    trapHandler: null,
  };

  function renderChatElement(el, handleAction) {
    const chat = el && typeof el === "object" ? el : {};
    const wrapper = document.createElement("div");
    wrapper.className = "ui-element ui-chat";
    const style = chat.style === "plain" ? "plain" : "bubbles";
    wrapper.dataset.chatStyle = style;
    wrapper.classList.add(`ui-chat-style-${style}`);

    const children = Array.isArray(chat.children) ? chat.children : [];
    const chatConfig = {
      ...chat,
      _hasCitationPanel: children.some((child) => child && child.type === "citations"),
    };
    children.forEach((child) => {
      const node = renderChatChild(child, handleAction, chatConfig);
      if (node) wrapper.appendChild(node);
    });

    return wrapper;
  }

  function renderChatChild(child, handleAction, chatConfig) {
    if (!child || !child.type) return null;
    if (child.type === "messages") return renderMessages(child, chatConfig, handleAction);
    if (child.type === "composer") return renderComposer(child, handleAction);
    if (child.type === "thinking") return renderThinking(child, chatConfig);
    if (child.type === "citations") return renderCitations(child);
    if (child.type === "memory") return renderMemory(child);
    return null;
  }

  function renderMessages(child, chatConfig, handleAction) {
    const container = document.createElement("div");
    const style = chatConfig && chatConfig.style === "plain" ? "plain" : "bubbles";
    container.className = `ui-chat-messages ui-chat-messages-${style}`;
    const messages = Array.isArray(child.messages) ? child.messages : [];
    const controlContract = resolveMessageControlContract(child);
    if (!messages.length) {
      if (chatConfig && chatConfig._hasCitationPanel) {
        container.appendChild(renderNoSourcesPanel());
      } else {
        const empty = document.createElement("div");
        empty.className = "ui-chat-empty";
        empty.textContent = "No messages yet.";
        container.appendChild(empty);
      }
      return container;
    }
    let previousRole = "";
    messages.forEach((message) => {
      const roleValue = normalizeMessageRole(message && message.role);
      const messageId = messageIdentity(message);
      const grouped =
        chatConfig && chatConfig.group_messages !== false && !message.group_start
          ? true
          : chatConfig && chatConfig.group_messages !== false && previousRole === roleValue;
      const groupStart = !grouped;
      previousRole = roleValue;
      const row = document.createElement("div");
      row.className = `ui-chat-message role-${roleValue} ${groupStart ? "group-start" : "group-continue"}`;
      if (messageId) {
        row.dataset.messageId = messageId;
      }
      const isActiveMessage = Boolean(controlContract.activeMessageId && messageId && controlContract.activeMessageId === messageId);
      if (isActiveMessage) {
        row.classList.add("active-branch");
      }
      const showAvatar = Boolean(chatConfig && chatConfig.show_avatars && groupStart);
      if (showAvatar) {
        const avatar = document.createElement("div");
        avatar.className = `ui-chat-avatar role-${roleValue}`;
        avatar.textContent = roleAvatarText(roleValue);
        row.appendChild(avatar);
      }
      const bubble = document.createElement("div");
      bubble.className = "ui-chat-bubble";
      const role = document.createElement("div");
      role.className = "ui-chat-role";
      role.textContent = roleValue;
      const content = document.createElement("div");
      content.className = "ui-chat-content";
      const fullText = typeof message.content === "string" ? message.content : "";
      const actions = normalizeMessageActions(message && message.actions, chatConfig && chatConfig.actions);
      if (actions.includes("expand") && fullText.length > 280) {
        setExpandedContent(content, fullText, false);
      } else {
        content.textContent = fullText;
      }
      const isStreamingMessage =
        Boolean(chatConfig && chatConfig.streaming) &&
        Boolean(message && message.streaming === true) &&
        roleValue === "assistant";
      if (isStreamingMessage) {
        row.classList.add("is-streaming");
      }
      bubble.appendChild(role);
      bubble.appendChild(content);
      if (isStreamingMessage) {
        renderStreamingContent(content, message, () => revealMessageCitations(row));
      }
      if (Object.prototype.hasOwnProperty.call(message, "trust") && typeof root.renderTrustIndicatorElement === "function") {
        const trustNode = root.renderTrustIndicatorElement({
          type: "trust_indicator",
          value: message.trust,
          compact: true,
        });
        trustNode.classList.add("ui-chat-trust-row");
        bubble.appendChild(trustNode);
      }
      renderMessageAttachments(bubble, message, chatConfig, { deferCitations: isStreamingMessage });
      if (typeof message.error === "string" && message.error.trim()) {
        const errorSurface = document.createElement("div");
        errorSurface.className = "ui-chat-error-surface";
        errorSurface.textContent = "Something went wrong while generating this response.";
        bubble.appendChild(errorSurface);
      }
      if (message.created) {
        const created = document.createElement("div");
        created.className = "ui-chat-created";
        created.textContent = String(message.created);
        bubble.appendChild(created);
      }
      renderMessageGraphControls(bubble, {
        actionContract: controlContract,
        handleAction: handleAction,
        isActiveMessage: isActiveMessage,
        message: message,
        messageId: messageId,
        role: roleValue,
      });
      renderMessageActions(bubble, actions, message, content);
      row.appendChild(bubble);
      container.appendChild(row);
    });
    return container;
  }

  function normalizeMessageRole(value) {
    const role = typeof value === "string" ? value.trim().toLowerCase() : "";
    if (!role) return "user";
    if (role === "assistant" || role === "system" || role === "tool" || role === "user") return role;
    return "user";
  }

  function roleAvatarText(role) {
    if (role === "assistant") return "AI";
    if (role === "system") return "S";
    if (role === "tool") return "T";
    return "U";
  }

  function normalizeMessageActions(raw, defaults) {
    const values = Array.isArray(raw) ? raw : Array.isArray(defaults) ? defaults : [];
    const allowed = new Set(["copy", "expand", "view_sources"]);
    const normalized = [];
    values.forEach((entry) => {
      if (typeof entry !== "string") return;
      const value = entry.trim().toLowerCase();
      if (!allowed.has(value) || normalized.includes(value)) return;
      normalized.push(value);
    });
    return normalized;
  }

  function messageIdentity(message) {
    if (!message || typeof message !== "object") return "";
    if (typeof message.id !== "string") return "";
    const text = message.id.trim();
    return text || "";
  }

  function normalizeControlAction(actionId, type) {
    if (typeof actionId !== "string") return null;
    const text = actionId.trim();
    if (!text) return null;
    return { id: text, type: type };
  }

  function resolveMessageControlContract(child) {
    const payload = child && typeof child === "object" ? child : {};
    const phaseRaw = typeof payload.stream_phase === "string" ? payload.stream_phase.trim().toLowerCase() : "";
    return {
      activeMessageId: typeof payload.active_message_id === "string" ? payload.active_message_id.trim() : "",
      branchAction: normalizeControlAction(payload.branch_action_id, "chat.branch.select"),
      regenerateAction: normalizeControlAction(payload.regenerate_action_id, "chat.message.regenerate"),
      streamCancelAction: normalizeControlAction(payload.stream_cancel_action_id, "chat.stream.cancel"),
      streamCancelRequested: Boolean(payload.stream_cancel_requested),
      streamPhase: phaseRaw,
    };
  }

  function shouldRenderStreamCancel(contract, isActiveMessage) {
    if (!isActiveMessage || !contract || !contract.streamCancelAction) return false;
    if (contract.streamCancelRequested) return false;
    return contract.streamPhase === "streaming" || contract.streamPhase === "thinking";
  }

  function renderMessageGraphControls(container, options) {
    const config = options && typeof options === "object" ? options : {};
    const contract = config.actionContract && typeof config.actionContract === "object" ? config.actionContract : null;
    const handleAction = typeof config.handleAction === "function" ? config.handleAction : null;
    const messageId = typeof config.messageId === "string" ? config.messageId : "";
    const role = typeof config.role === "string" ? config.role : "";
    const isActiveMessage = Boolean(config.isActiveMessage);
    if (!contract || !handleAction) return;
    const controls = [];
    if (contract.branchAction && messageId && !isActiveMessage) {
      controls.push({
        action: contract.branchAction,
        label: "Switch branch",
        payload: { message_id: messageId },
      });
    }
    if (contract.regenerateAction && messageId && role === "assistant") {
      controls.push({
        action: contract.regenerateAction,
        label: "Regenerate",
        payload: { message_id: messageId },
      });
    }
    if (shouldRenderStreamCancel(contract, isActiveMessage)) {
      controls.push({
        action: contract.streamCancelAction,
        label: "Stop",
        payload: { message_id: messageId },
      });
    }
    if (!controls.length) return;
    const bar = document.createElement("div");
    bar.className = "ui-chat-message-controls";
    controls.forEach((entry) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn small ghost";
      button.textContent = entry.label;
      button.onclick = async () => {
        button.disabled = true;
        try {
          await handleAction(entry.action, entry.payload, button);
        } finally {
          button.disabled = false;
        }
      };
      bar.appendChild(button);
    });
    container.appendChild(bar);
  }

  function renderMessageAttachments(container, message, chatConfig, options) {
    const config = options && typeof options === "object" ? options : {};
    const attachmentsEnabled = Boolean(chatConfig && chatConfig.attachments);
    const attachments = Array.isArray(message && message.attachments) ? message.attachments : [];
    const citations = collectMessageCitations(message);
    if (!attachmentsEnabled && !citations.length) return;
    const block = document.createElement("div");
    block.className = "ui-chat-attachments";
    if (citations.length && typeof root.renderCitationChipsElement === "function") {
      const chips = root.renderCitationChipsElement({
        type: "citation_chips",
        citations: citations,
        enhanced: !chatConfig || chatConfig.citations_enhanced !== false,
        compact: true,
      });
      if (config.deferCitations && attachments.filter((entry) => entry && entry.type !== "citation").length === 0) {
        block.dataset.streamVisible = "false";
      }
      block.appendChild(chips);
    }
    attachments.forEach((attachment) => {
      if (!attachment || typeof attachment !== "object") return;
      const type = typeof attachment.type === "string" ? attachment.type : "";
      if (type === "citation") return;
      if (type === "file") {
        const file = document.createElement("a");
        file.className = "ui-chat-attachment-file";
        const name = typeof attachment.name === "string" && attachment.name ? attachment.name : "File";
        file.textContent = name;
        if (typeof attachment.url === "string" && attachment.url) {
          file.href = attachment.url;
          file.target = "_blank";
          file.rel = "noopener noreferrer";
        } else {
          file.href = "#";
        }
        block.appendChild(file);
        return;
      }
      if (type === "image" && typeof attachment.url === "string" && attachment.url) {
        const image = document.createElement("img");
        image.className = "ui-chat-attachment-image";
        image.src = attachment.url;
        image.alt = typeof attachment.alt === "string" ? attachment.alt : "Attachment";
        block.appendChild(image);
      }
    });
    if (block.children.length > 0) container.appendChild(block);
  }

  function renderMessageActions(container, actions, message, contentNode) {
    if (!actions.length) return;
    const bar = document.createElement("div");
    bar.className = "ui-chat-message-actions";
    actions.forEach((action) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn small ghost";
      if (action === "copy") {
        button.textContent = "Copy";
        button.onclick = async () => {
          const text = typeof message.content === "string" ? message.content : "";
          await copyToClipboard(text);
          button.textContent = "Copied";
          setTimeout(() => {
            button.textContent = "Copy";
          }, 800);
        };
      } else if (action === "expand") {
        button.textContent = "Expand";
        button.onclick = () => {
          const expanded = contentNode.dataset.expanded === "true";
          setExpandedContent(contentNode, contentNode.dataset.fullText || contentNode.textContent || "", !expanded);
          button.textContent = expanded ? "Expand" : "Collapse";
        };
      } else if (action === "view_sources") {
        button.textContent = "Sources";
        button.onclick = () => {
          const citations = collectMessageCitations(message);
          if (!citations.length) {
            button.textContent = "No sources";
            setTimeout(() => {
              button.textContent = "Sources";
            }, 1000);
            return;
          }
          openCitationPreview(citations[0], button, citations);
        };
      }
      bar.appendChild(button);
    });
    container.appendChild(bar);
  }

  function setExpandedContent(node, fullText, expanded) {
    node.dataset.fullText = fullText;
    node.dataset.expanded = expanded ? "true" : "false";
    if (expanded || fullText.length <= 280) {
      node.textContent = fullText;
      return;
    }
    node.textContent = `${fullText.slice(0, 280)}...`;
  }

  function renderNoSourcesPanel() {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-empty-sources-panel";
    const title = document.createElement("div");
    title.className = "ui-empty-sources-title";
    title.textContent = "No sources available";
    const text = document.createElement("div");
    text.className = "ui-empty-sources-text";
    text.textContent = "Upload a document to ground answers with citations.";
    const actions = document.createElement("div");
    actions.className = "ui-empty-sources-actions";
    const upload = document.createElement("button");
    upload.type = "button";
    upload.className = "btn small";
    upload.textContent = "Upload document";
    upload.onclick = () => {
      const fileInput = document.querySelector(".ui-upload-input");
      if (fileInput && typeof fileInput.click === "function") {
        fileInput.click();
        return;
      }
      document.dispatchEvent(new CustomEvent("n3:upload-document"));
    };
    actions.appendChild(upload);
    wrapper.appendChild(title);
    wrapper.appendChild(text);
    wrapper.appendChild(actions);
    return wrapper;
  }

  function revealMessageCitations(rowNode) {
    if (!rowNode) return;
    const hiddenBlocks = rowNode.querySelectorAll('.ui-chat-attachments[data-stream-visible="false"]');
    hiddenBlocks.forEach((block) => {
      block.dataset.streamVisible = "true";
    });
  }

  function collectMessageCitations(message) {
    const values = [];
    const seen = new Set();
    const pushUnique = (entry) => {
      const key = citationIdentity(entry);
      if (seen.has(key)) return;
      seen.add(key);
      values.push(entry);
    };
    const direct = normalizeCitationEntries(message && message.citations);
    direct.forEach((entry) => pushUnique(entry));
    const attachments = Array.isArray(message && message.attachments) ? message.attachments : [];
    attachments.forEach((attachment) => {
      if (!attachment || attachment.type !== "citation") return;
      normalizeCitationEntries([attachment]).forEach((entry) => pushUnique(entry));
    });
    return values;
  }

  function citationIdentity(entry) {
    const citationId = typeof entry.citation_id === "string" ? entry.citation_id : "";
    const title = typeof entry.title === "string" ? entry.title : "";
    const sourceId = typeof entry.source_id === "string" ? entry.source_id : "";
    const url = typeof entry.url === "string" ? entry.url : "";
    const page = typeof entry.page_number === "number" || typeof entry.page_number === "string" ? String(entry.page_number) : "";
    return [citationId, title, sourceId, url, page].join("|");
  }

  function sameCitationEntry(left, right) {
    const leftId = left && typeof left.citation_id === "string" ? left.citation_id.trim() : "";
    const rightId = right && typeof right.citation_id === "string" ? right.citation_id.trim() : "";
    if (leftId && rightId) {
      return leftId === rightId;
    }
    return citationIdentity(left) === citationIdentity(right);
  }

  async function copyToClipboard(value) {
    const text = typeof value === "string" ? value : "";
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        return;
      } catch (_err) {}
    }
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "true");
    area.style.position = "absolute";
    area.style.left = "-9999px";
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    document.body.removeChild(area);
  }

  function renderStreamingContent(contentNode, message, onComplete) {
    const fullText = typeof message.content === "string" ? message.content : "";
    const tokenValues = Array.isArray(message.tokens)
      ? message.tokens.filter((entry) => typeof entry === "string")
      : fullText.split(/(\s+)/).filter((entry) => entry.length > 0);
    if (!tokenValues.length) {
      contentNode.textContent = fullText;
      contentNode.dataset.streamPhase = "complete";
      if (typeof onComplete === "function") onComplete();
      return;
    }
    contentNode.textContent = "";
    contentNode.dataset.streamPhase = "thinking";
    const thinking = document.createElement("span");
    thinking.className = "ui-chat-stream-thinking";
    const dot = document.createElement("span");
    dot.className = "ui-chat-stream-thinking-dot";
    thinking.appendChild(dot);
    contentNode.appendChild(thinking);
    let cursor = 0;
    let finalized = false;
    const complete = () => {
      if (finalized) return;
      finalized = true;
      contentNode.dataset.streamPhase = "complete";
      if (typeof onComplete === "function") onComplete();
    };
    const interval = window.setInterval(() => {
      if (!contentNode.isConnected) {
        window.clearInterval(interval);
        complete();
        return;
      }
      if (cursor === 0) {
        contentNode.textContent = "";
        contentNode.dataset.streamPhase = "streaming";
      }
      const token = tokenValues[cursor];
      contentNode.textContent += token;
      cursor += 1;
      if (cursor >= tokenValues.length) {
        window.clearInterval(interval);
        complete();
      }
    }, 14);
  }

  function renderComposer(child, handleAction) {
    const form = document.createElement("form");
    form.className = "ui-chat-composer";
    const composerState = normalizeComposerState(child);
    const actionType =
      child && typeof child.action_type === "string" && child.action_type
        ? child.action_type
        : child &&
            child.action &&
            typeof child.action.type === "string" &&
            child.action.type
          ? child.action.type
          : "call_flow";
    const actionFlow =
      child && typeof child.flow === "string" && child.flow
        ? child.flow
        : child &&
            child.action &&
            typeof child.action.flow === "string" &&
            child.action.flow
          ? child.action.flow
          : "";
    const fields = normalizeComposerFields(child);
    const inputs = new Map();
    fields.forEach((field) => {
      const name = field.name || "message";
      const placeholder = name === "message" ? "Type a message" : String(name);
      const input = name === "message" ? document.createElement("textarea") : document.createElement("input");
      if (input.tagName.toLowerCase() === "input") {
        input.type = "text";
      } else {
        input.className = "ui-chat-composer-message";
        input.rows = 1;
        input.addEventListener("keydown", (event) => {
          if (event.key !== "Enter" || event.shiftKey) return;
          event.preventDefault();
          if (typeof form.requestSubmit === "function") {
            form.requestSubmit();
          } else {
            form.dispatchEvent(new Event("submit", { cancelable: true }));
          }
        });
        if (name === "message" && composerState.draft) {
          input.value = composerState.draft;
        }
      }
      input.placeholder = placeholder;
      input.setAttribute("aria-label", placeholder);
      inputs.set(name, input);
      form.appendChild(input);
    });
    const advancedControls = actionType === "chat.message.send" ? buildComposerAdvancedControls(composerState) : null;
    if (advancedControls) {
      form.appendChild(advancedControls.node);
    }
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
      if (advancedControls) {
        const advancedPayload = advancedControls.read();
        payload.attachments = advancedPayload.attachments;
        payload.tools = advancedPayload.tools;
        payload.web_search = advancedPayload.web_search;
      }
      inputs.forEach((input) => {
        if (input) input.value = "";
      });
      const action = { id: child.action_id, type: actionType };
      if (actionFlow) {
        action.flow = actionFlow;
      }
      await handleAction(
        action,
        payload,
        button
      );
      const messageInput = inputs.get("message");
      if (messageInput && typeof messageInput.focus === "function") {
        messageInput.focus();
      }
    };
    return form;
  }

  function normalizeComposerState(child) {
    const raw =
      child && typeof child === "object" && child.composer_state && typeof child.composer_state === "object"
        ? child.composer_state
        : {};
    return {
      attachments: normalizeComposerTokenList(raw.attachments),
      draft: typeof raw.draft === "string" ? raw.draft : "",
      tools: normalizeComposerTokenList(raw.tools),
      web_search: Boolean(raw.web_search),
    };
  }

  function normalizeComposerTokenList(value) {
    const source = Array.isArray(value) ? value : [];
    const normalized = [];
    const seen = new Set();
    source.forEach((entry) => {
      if (typeof entry !== "string") return;
      const text = entry.trim();
      if (!text || seen.has(text)) return;
      seen.add(text);
      normalized.push(text);
    });
    return normalized;
  }

  function buildComposerAdvancedControls(state) {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-chat-composer-advanced";
    const attachmentsEditor = buildComposerListEditor("Attachments", state.attachments, "Add attachment id");
    const toolsEditor = buildComposerListEditor("Tools", state.tools, "Add tool id");
    wrapper.appendChild(attachmentsEditor.node);
    wrapper.appendChild(toolsEditor.node);

    const webSearchRow = document.createElement("label");
    webSearchRow.className = "ui-chat-composer-toggle";
    const webSearchToggle = document.createElement("input");
    webSearchToggle.type = "checkbox";
    webSearchToggle.checked = Boolean(state.web_search);
    const webSearchText = document.createElement("span");
    webSearchText.textContent = "Web search";
    webSearchRow.appendChild(webSearchToggle);
    webSearchRow.appendChild(webSearchText);
    wrapper.appendChild(webSearchRow);

    return {
      node: wrapper,
      read: () => ({
        attachments: attachmentsEditor.values(),
        tools: toolsEditor.values(),
        web_search: webSearchToggle.checked === true,
      }),
    };
  }

  function buildComposerListEditor(label, initialValues, placeholder) {
    const values = Array.isArray(initialValues) ? initialValues.slice() : [];
    const container = document.createElement("div");
    container.className = "ui-chat-composer-list";
    const title = document.createElement("div");
    title.className = "ui-chat-composer-list-title";
    title.textContent = label;
    container.appendChild(title);
    const chips = document.createElement("div");
    chips.className = "ui-chat-composer-list-values";
    container.appendChild(chips);
    const inputRow = document.createElement("div");
    inputRow.className = "ui-chat-composer-list-input";
    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = placeholder;
    input.setAttribute("aria-label", placeholder);
    const addButton = document.createElement("button");
    addButton.type = "button";
    addButton.className = "btn small ghost";
    addButton.textContent = "Add";
    const renderValues = () => {
      chips.textContent = "";
      if (!values.length) {
        const empty = document.createElement("span");
        empty.className = "ui-chat-composer-list-empty";
        empty.textContent = "none";
        chips.appendChild(empty);
        return;
      }
      values.forEach((entry, index) => {
        const chip = document.createElement("span");
        chip.className = "ui-chat-composer-chip";
        const text = document.createElement("span");
        text.textContent = entry;
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "btn small ghost";
        remove.textContent = "x";
        remove.setAttribute("aria-label", `Remove ${label} ${entry}`);
        remove.onclick = () => {
          values.splice(index, 1);
          renderValues();
        };
        chip.appendChild(text);
        chip.appendChild(remove);
        chips.appendChild(chip);
      });
    };
    const addValue = () => {
      const nextValue = typeof input.value === "string" ? input.value.trim() : "";
      if (!nextValue || values.includes(nextValue)) {
        input.value = "";
        return;
      }
      values.push(nextValue);
      input.value = "";
      renderValues();
    };
    addButton.onclick = () => addValue();
    input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      addValue();
    });
    inputRow.appendChild(input);
    inputRow.appendChild(addButton);
    container.appendChild(inputRow);
    renderValues();
    return {
      node: container,
      values: () => values.slice(),
    };
  }

  function resolveCitationTarget(entry) {
    if (!entry) return null;
    const chunkId = textValue(entry.chunk_id) || textValue(entry.source_id) || null;
    let documentId =
      textValue(entry.document_id) ||
      textValue(entry.documentId) ||
      textValue(entry.upload_id) ||
      null;
    const pageNumber = toPageNumber(entry.page_number || entry.page);
    if (!documentId && chunkId) {
      const parts = chunkId.split(":");
      if (parts.length > 1 && parts[0]) {
        documentId = parts[0];
      }
    }
    if (documentId && pageNumber) {
      return { documentId: documentId, pageNumber: pageNumber, chunkId: chunkId };
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

    const tabs = document.createElement("div");
    tabs.className = "ui-citation-preview-tabs";
    const sourcesTab = document.createElement("button");
    sourcesTab.type = "button";
    sourcesTab.className = "ui-citation-preview-tab";
    sourcesTab.dataset.tab = "sources";
    sourcesTab.textContent = "Sources";
    const previewTab = document.createElement("button");
    previewTab.type = "button";
    previewTab.className = "ui-citation-preview-tab";
    previewTab.dataset.tab = "preview";
    previewTab.textContent = "Preview";
    const explainTab = document.createElement("button");
    explainTab.type = "button";
    explainTab.className = "ui-citation-preview-tab";
    explainTab.dataset.tab = "explain";
    explainTab.textContent = "Explain";
    sourcesTab.onclick = () => setCitationPreviewTab("sources");
    previewTab.onclick = () => setCitationPreviewTab("preview");
    explainTab.onclick = () => setCitationPreviewTab("explain");
    tabs.appendChild(sourcesTab);
    tabs.appendChild(previewTab);
    tabs.appendChild(explainTab);
    panel.appendChild(tabs);

    const sourcesView = document.createElement("div");
    sourcesView.className = "ui-citation-preview-view ui-citation-preview-sources-view";
    const sourcesList = document.createElement("div");
    sourcesList.className = "ui-citation-preview-sources";
    sourcesView.appendChild(sourcesList);
    panel.appendChild(sourcesView);

    const previewView = document.createElement("div");
    previewView.className = "ui-citation-preview-view ui-citation-preview-preview-view";

    const meta = document.createElement("div");
    meta.className = "ui-citation-preview-meta";
    previewView.appendChild(meta);

    const snippetSection = document.createElement("div");
    snippetSection.className = "ui-citation-preview-section";
    const snippetLabel = document.createElement("div");
    snippetLabel.className = "ui-citation-preview-label";
    snippetLabel.textContent = "Snippet";
    const snippet = document.createElement("div");
    snippet.className = "ui-citation-preview-snippet";
    snippetSection.appendChild(snippetLabel);
    snippetSection.appendChild(snippet);
    previewView.appendChild(snippetSection);

    const textSection = document.createElement("div");
    textSection.className = "ui-citation-preview-section";
    const textLabel = document.createElement("div");
    textLabel.className = "ui-citation-preview-label";
    textLabel.textContent = "Page text";
    const notice = document.createElement("div");
    notice.className = "ui-citation-preview-notice";
    notice.textContent = "";
    notice.hidden = true;
    const pageText = document.createElement("div");
    pageText.className = "ui-citation-preview-text";
    textSection.appendChild(textLabel);
    textSection.appendChild(notice);
    textSection.appendChild(pageText);
    previewView.appendChild(textSection);

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
    previewView.appendChild(controls);

    const frame = document.createElement("iframe");
    frame.className = "ui-citation-preview-frame";
    frame.title = "Document preview";
    previewView.appendChild(frame);

    const error = document.createElement("div");
    error.className = "ui-citation-preview-error";
    previewView.appendChild(error);
    panel.appendChild(previewView);

    const explainView = document.createElement("div");
    explainView.className = "ui-citation-preview-view ui-citation-preview-explain-view";
    const explainText = document.createElement("div");
    explainText.className = "ui-citation-preview-explain";
    explainText.textContent = "This panel explains why a source was selected.";
    explainView.appendChild(explainText);
    panel.appendChild(explainView);

    overlay.appendChild(panel);
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) closeCitationPreview();
    });
    overlay.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeCitationPreview();
        return;
      }
      trapCitationPreviewFocus(event);
    });
    document.body.appendChild(overlay);

    previewState.container = overlay;
    previewState.panel = panel;
    previewState.title = title;
    previewState.tabs = tabs;
    previewState.sourcesView = sourcesView;
    previewState.previewView = previewView;
    previewState.explainView = explainView;
    previewState.explainText = explainText;
    previewState.sourcesList = sourcesList;
    previewState.tabButtons = [sourcesTab, previewTab, explainTab];
    previewState.meta = meta;
    previewState.snippet = snippet;
    previewState.pageText = pageText;
    previewState.pageNotice = notice;
    previewState.pageLabel = pageLabel;
    previewState.prevButton = prevBtn;
    previewState.nextButton = nextBtn;
    previewState.frame = frame;
    previewState.error = error;
    previewState.sourceItems = [];

    prevBtn.onclick = () => navigatePreviewPage(-1);
    nextBtn.onclick = () => navigatePreviewPage(1);
    setCitationPreviewTab("sources");

    return previewState;
  }

  function trapCitationPreviewFocus(event) {
    if (event.key !== "Tab") return;
    if (!(window.matchMedia && window.matchMedia("(max-width: 960px)").matches)) return;
    const preview = previewState;
    if (!preview.panel) return;
    const focusable = Array.from(
      preview.panel.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
    ).filter((el) => !el.disabled && !el.hidden);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
      return;
    }
    if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function setCitationPreviewTab(tab) {
    const preview = ensureCitationPreview();
    const selected = tab === "preview" || tab === "explain" ? tab : "sources";
    preview.tabButtons.forEach((button) => {
      const active = button.dataset.tab === selected;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
    preview.sourcesView.hidden = selected !== "sources";
    preview.previewView.hidden = selected !== "preview";
    preview.explainView.hidden = selected !== "explain";
  }

  function renderPreviewSources(citations, selectedIndex) {
    const preview = ensureCitationPreview();
    preview.sourcesList.textContent = "";
    preview.sourceItems = [];
    citations.forEach((entry, index) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "ui-citation-preview-source";
      if (typeof entry.citation_id === "string" && entry.citation_id) {
        item.dataset.citationId = entry.citation_id;
      }
      if (index === selectedIndex) item.classList.add("active");
      item.onclick = () => {
        selectPreviewCitation(index, { openPreviewTab: true });
      };
      const title = document.createElement("div");
      title.className = "ui-citation-preview-source-title";
      title.textContent = entry.title || `Source ${index + 1}`;
      const meta = document.createElement("div");
      meta.className = "ui-citation-preview-source-meta";
      const target = resolveCitationTarget(entry);
      if (target && target.pageNumber) {
        meta.textContent = `Page ${target.pageNumber}`;
      } else if (entry.url) {
        meta.textContent = entry.url;
      } else if (entry.source_id) {
        meta.textContent = entry.source_id;
      } else {
        meta.textContent = "Preview unavailable";
      }
      const snippet = document.createElement("div");
      snippet.className = "ui-citation-preview-source-snippet";
      snippet.textContent = formatSnippet(entry.snippet || "", "");
      item.appendChild(title);
      item.appendChild(meta);
      item.appendChild(snippet);
      preview.sourcesList.appendChild(item);
      preview.sourceItems.push(item);
    });
  }

  function selectPreviewCitation(index, options) {
    const preview = ensureCitationPreview();
    const config = options && typeof options === "object" ? options : {};
    if (!Array.isArray(preview.citations) || !preview.citations.length) return;
    const bounded = Math.max(0, Math.min(index, preview.citations.length - 1));
    preview.selectedCitationIndex = bounded;
    preview.sourceItems.forEach((item, idx) => {
      item.classList.toggle("active", idx === bounded);
    });
    const selectedItem = preview.sourceItems[bounded];
    if (selectedItem && typeof selectedItem.scrollIntoView === "function") {
      selectedItem.scrollIntoView({ block: "nearest" });
    }
    const entry = preview.citations[bounded];
    preview.entrySnippet = typeof entry.snippet === "string" ? entry.snippet : "";
    preview.title.textContent = entry.title || "Source";
    preview.explainText.textContent =
      typeof entry.explain === "string" && entry.explain.trim()
        ? entry.explain
        : "The answer cited this source for matching context.";
    const target = resolveCitationTarget(entry);
    if (!target) {
      preview.meta.textContent = "Preview unavailable";
      preview.error.textContent = "Preview unavailable for this citation.";
      preview.snippet.textContent = formatSnippet(preview.entrySnippet, "");
      preview.pageText.textContent = "No extracted text for this page.";
      preview.pageLabel.textContent = "";
      preview.prevButton.disabled = true;
      preview.nextButton.disabled = true;
    } else {
      preview.chunkId = target.chunkId || null;
      preview.citationId = typeof entry.citation_id === "string" ? entry.citation_id : null;
      loadPreviewPage(target.documentId, target.pageNumber, preview.chunkId, preview.citationId);
      if (typeof root.applyCitationDeepLinkState === "function") {
        root.applyCitationDeepLinkState({
          citation_id: preview.citationId || "",
          document_id: target.documentId,
          page_number: target.pageNumber,
        });
      }
    }
    if (config.openPreviewTab) {
      setCitationPreviewTab("preview");
    }
  }

  function openCitationPreview(entry, opener, citationSet) {
    if (!entry || typeof entry !== "object") return;
    const preview = ensureCitationPreview();
    preview.returnFocus = opener || document.activeElement;
    const citations = normalizeCitationEntries(Array.isArray(citationSet) && citationSet.length ? citationSet : [entry]);
    preview.citations = citations;
    const selectedIndex = Math.max(
      0,
      citations.findIndex((item) => sameCitationEntry(item, entry))
    );
    renderPreviewSources(citations, selectedIndex);
    selectPreviewCitation(selectedIndex, { openPreviewTab: false });
    preview.container.classList.remove("hidden");
    preview.container.setAttribute("aria-hidden", "false");
    setCitationPreviewTab("sources");
    preview.panel.focus();
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
    preview.chunkId = null;
    preview.citationId = null;
    preview.citations = [];
    preview.selectedCitationIndex = -1;
    preview.sourceItems = [];
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
    loadPreviewPage(preview.documentId, nextPage, preview.chunkId, preview.citationId);
  }

  async function loadPreviewPage(documentId, pageNumber, chunkId, citationId) {
    const preview = ensureCitationPreview();
    preview.documentId = documentId;
    preview.pageNumber = pageNumber;
    preview.citationId = citationId || null;
    preview.meta.textContent = "Loading page...";
    preview.error.textContent = "";
    preview.pageLabel.textContent = "";
    preview.prevButton.disabled = true;
    preview.nextButton.disabled = true;
    preview.pageText.textContent = "";
    preview.pageNotice.textContent = "";
    preview.pageNotice.hidden = true;
    preview.snippet.textContent = "Loading snippet...";
    preview.frame.removeAttribute("src");

    try {
      const url =
        typeof root.buildPdfPreviewRequestUrl === "function"
          ? root.buildPdfPreviewRequestUrl(documentId, pageNumber, chunkId, citationId)
          : (() => {
              const params = new URLSearchParams();
              if (chunkId) params.set("chunk_id", chunkId);
              if (citationId) params.set("citation_id", citationId);
              const query = params.toString();
              const base = `/api/documents/${encodeURIComponent(documentId)}/pages/${pageNumber}`;
              return query ? `${base}?${query}` : base;
            })();
      const response = await fetch(url);
      const payload = await response.json();
      if (!payload || typeof payload !== "object") {
        throw new Error(`Preview request failed (${response.status})`);
      }
      if (typeof payload.error_code === "string" && payload.error_code) {
        const message = typeof payload.message === "string" && payload.message ? payload.message : "Preview request failed.";
        throw new Error(`${payload.error_code}: ${message}`);
      }
      if (!response.ok) {
        throw new Error(`Preview request failed (${response.status})`);
      }
      if (payload.status === "unavailable") {
        const docMeta = payload.doc_meta && typeof payload.doc_meta === "object" ? payload.doc_meta : {};
        const fallback = typeof payload.fallback_snippet === "string" ? payload.fallback_snippet : "";
        const reason =
          typeof payload.reason === "string" && payload.reason.trim() ? payload.reason.trim() : "Preview unavailable for this citation.";
        const unavailablePage = Number(docMeta.page_number) || pageNumber;
        const unavailablePageCount = Number(docMeta.page_count) || unavailablePage;
        preview.pageCount = unavailablePageCount;
        preview.pageNumber = unavailablePage;
        preview.pageLabel.textContent = unavailablePageCount > 0 ? `Page ${unavailablePage} of ${unavailablePageCount}` : "";
        const name = docMeta.source_name || preview.title.textContent || "Document";
        preview.meta.textContent = `${name} - Preview unavailable`;
        preview.error.textContent = reason;
        preview.prevButton.disabled = true;
        preview.nextButton.disabled = true;
        preview.frame.removeAttribute("src");
        preview.pageNotice.hidden = true;
        preview.pageNotice.textContent = "";
        preview.pageText.textContent = fallback || "No extracted text for this page.";
        preview.snippet.textContent = formatSnippet(preview.entrySnippet, fallback);
        return;
      }

      if (payload.status !== "ok" && payload.ok !== true) {
        throw new Error("Preview response was not ok.");
      }
      const previewPayload = payload.preview && typeof payload.preview === "object" ? payload.preview : payload;
      const doc = previewPayload.document || payload.document || {};
      const page = previewPayload.page || payload.page || {};
      const pageCount = Number(doc.page_count) || pageNumber;
      preview.pageCount = pageCount;
      preview.pageNumber = Number(page.number) || pageNumber;
      preview.pageLabel.textContent = `Page ${preview.pageNumber} of ${pageCount}`;
      const name = doc.source_name || preview.title.textContent || "Document";
      preview.meta.textContent = `${name} - ${preview.pageLabel.textContent}`;
      preview.prevButton.disabled = preview.pageNumber <= 1;
      preview.nextButton.disabled = preview.pageNumber >= pageCount;
      preview.frame.src =
        previewPayload.pdf_url || payload.pdf_url || `/api/documents/${encodeURIComponent(documentId)}/pdf#page=${preview.pageNumber}`;
      const pageText = typeof page.text === "string" ? page.text : "";
      const highlightsSource = Array.isArray(previewPayload.highlights) ? previewPayload.highlights : payload.highlights;
      const highlights = Array.isArray(highlightsSource) ? highlightsSource : [];
      const fallbackColorIndex =
        typeof root.citationColorIndex === "function" ? root.citationColorIndex(preview.citationId || "", 8) : 0;
      renderPageText(preview.pageText, pageText, highlights, fallbackColorIndex);
      setHighlightNotice(preview.pageNotice, highlights);
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

  function renderPageText(container, pageText, highlights, fallbackColorIndex) {
    if (!container) return;
    const text = typeof pageText === "string" ? pageText : "";
    container.textContent = "";
    if (!text) {
      container.textContent = "No extracted text for this page.";
      return;
    }
    const ranges = normalizeHighlightRanges(highlights, text.length, fallbackColorIndex);
    if (!ranges.length) {
      container.textContent = text;
      return;
    }
    const fragment = document.createDocumentFragment();
    let cursor = 0;
    ranges.forEach((range) => {
      if (range.start > cursor) {
        fragment.appendChild(document.createTextNode(text.slice(cursor, range.start)));
      }
      const mark = document.createElement("mark");
      mark.className = "ui-citation-highlight";
      mark.classList.add(`ui-citation-highlight-${range.colorIndex}`);
      mark.textContent = text.slice(range.start, range.end);
      fragment.appendChild(mark);
      cursor = range.end;
    });
    if (cursor < text.length) {
      fragment.appendChild(document.createTextNode(text.slice(cursor)));
    }
    container.appendChild(fragment);
  }

  function normalizeHighlightRanges(highlights, length, fallbackColorIndex) {
    const items = Array.isArray(highlights) ? highlights : [];
    const ranges = [];
    const fallbackColor = Number.isFinite(fallbackColorIndex) ? Math.trunc(fallbackColorIndex) % 8 : 0;
    items.forEach((item) => {
      if (!item || item.status !== "exact") return;
      const start = Number(item.start_char);
      const end = Number(item.end_char);
      if (!Number.isFinite(start) || !Number.isFinite(end)) return;
      const startValue = Math.max(0, Math.trunc(start));
      const endValue = Math.min(length, Math.trunc(end));
      if (endValue <= startValue) return;
      const itemColor = Number(item.color_index);
      const colorIndex = Number.isFinite(itemColor) ? Math.abs(Math.trunc(itemColor)) % 8 : fallbackColor;
      ranges.push({ start: startValue, end: endValue, colorIndex: colorIndex });
    });
    ranges.sort((a, b) => (a.start - b.start) || (a.end - b.end) || (a.colorIndex - b.colorIndex));
    const merged = [];
    ranges.forEach((range) => {
      const last = merged[merged.length - 1];
      if (!last || range.start > last.end || range.colorIndex !== last.colorIndex) {
        merged.push({ start: range.start, end: range.end, colorIndex: range.colorIndex });
      } else if (range.end > last.end) {
        last.end = range.end;
      }
    });
    return merged;
  }

  function setHighlightNotice(notice, highlights) {
    if (!notice) return;
    const items = Array.isArray(highlights) ? highlights : [];
    const hasExactText = items.some(
      (item) =>
        item &&
        item.status === "exact" &&
        Number.isFinite(Number(item.start_char)) &&
        Number.isFinite(Number(item.end_char))
    );
    const hasExactBBox = items.some((item) => item && item.status === "exact" && Array.isArray(item.bbox) && item.bbox.length === 4);
    const hasUnavailable = items.some((item) => item && item.status === "unavailable");
    if (hasExactBBox && !hasExactText) {
      notice.textContent = "Highlight is anchored in the PDF view.";
      notice.hidden = false;
      return;
    }
    if (hasUnavailable && !hasExactText) {
      notice.textContent = "Highlight unavailable for this citation.";
      notice.hidden = false;
      return;
    }
    notice.textContent = "";
    notice.hidden = true;
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

  function renderThinking(child, chatConfig) {
    const indicator = document.createElement("div");
    indicator.className = "ui-chat-thinking";
    const userVisible = Boolean(child.user_visible) || Boolean(chatConfig && chatConfig.streaming);
    const phase = typeof child.phase === "string" ? child.phase.trim().toLowerCase() : "";
    if (phase === "retrieving") {
      indicator.textContent = "Searching sources...";
    } else if (phase === "generating" || userVisible) {
      indicator.textContent = "Assistant is typing...";
    } else {
      indicator.textContent = "Thinking...";
    }
    if (userVisible) indicator.classList.add("user-visible");
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
    const citations = normalizeCitationEntries(child.citations);
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
      if (typeof entry.citation_id === "string" && entry.citation_id) {
        item.dataset.citationId = entry.citation_id;
      }
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
          openCitationPreview(entry, event.currentTarget, citations);
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

  function normalizeCitationEntries(raw) {
    const entries = Array.isArray(raw) ? raw : [];
    const normalized = [];
    entries.forEach((entry, idx) => {
      if (!entry || typeof entry !== "object") return;
      const title = typeof entry.title === "string" && entry.title.trim() ? entry.title.trim() : "Source";
      const payload = {
        citation_id:
          typeof entry.citation_id === "string" && entry.citation_id.trim()
            ? entry.citation_id.trim()
            : `citation.${idx + 1}`,
        index:
          typeof entry.index === "number" && Number.isFinite(entry.index)
            ? Math.max(1, Math.trunc(entry.index))
            : idx + 1,
        title: title,
      };
      if (typeof entry.url === "string" && entry.url.trim()) payload.url = entry.url.trim();
      if (typeof entry.source_id === "string" && entry.source_id.trim()) payload.source_id = entry.source_id.trim();
      if (typeof entry.snippet === "string" && entry.snippet.trim()) payload.snippet = entry.snippet.trim();
      if (typeof entry.explain === "string" && entry.explain.trim()) payload.explain = entry.explain.trim();
      if (typeof entry.chunk_id === "string" && entry.chunk_id.trim()) payload.chunk_id = entry.chunk_id.trim();
      if (typeof entry.document_id === "string" && entry.document_id.trim()) payload.document_id = entry.document_id.trim();
      if (typeof entry.deep_link_query === "string" && entry.deep_link_query.trim()) payload.deep_link_query = entry.deep_link_query.trim();
      if (typeof entry.preview_url === "string" && entry.preview_url.trim()) payload.preview_url = entry.preview_url.trim();
      if (typeof entry.page === "number" || typeof entry.page === "string") payload.page = entry.page;
      if (typeof entry.page_number === "number" || typeof entry.page_number === "string") payload.page_number = entry.page_number;
      if (typeof entry.color_index === "number" && Number.isFinite(entry.color_index)) payload.color_index = Math.abs(Math.trunc(entry.color_index)) % 8;
      normalized.push(payload);
    });
    return normalized;
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
  root.openCitationPreview = openCitationPreview;
  root.normalizeCitationEntries = normalizeCitationEntries;
  root.resolveCitationTarget = resolveCitationTarget;
})();
