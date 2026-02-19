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
    highlightColor: "",
    chunkId: null,
    citationId: null,
    citations: [],
    selectedCitationIndex: -1,
    tabButtons: [],
    trapHandler: null,
    lastDeepLinkKey: "",
  };

  function renderChatElement(el, handleAction) {
    const chat = el && typeof el === "object" ? el : {};
    const wrapper = document.createElement("div");
    wrapper.className = "ui-element ui-chat";
    const style = chat.style === "plain" ? "plain" : "bubbles";
    wrapper.dataset.chatStyle = style;
    wrapper.classList.add(`ui-chat-style-${style}`);

    const children = Array.isArray(chat.children) ? chat.children : [];
    const chatConfig = { ...chat };
    children.forEach((child) => {
      const node = renderChatChild(child, handleAction, chatConfig);
      if (node) wrapper.appendChild(node);
    });

    return wrapper;
  }

  function renderChatChild(child, handleAction, chatConfig) {
    if (!child || !child.type) return null;
    if (child.type === "messages") return renderMessages(child, chatConfig, handleAction);
    if (child.type === "composer") return renderComposer(child, handleAction, chatConfig);
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
    const renderedCitations = [];
    const controlContract = resolveMessageControlContract(child);
    if (!messages.length) {
      const empty = document.createElement("div");
      empty.className = "ui-chat-empty";
      const emptyText =
        child && typeof child.empty_text === "string" && child.empty_text.trim() ? child.empty_text.trim() : "No messages yet.";
      empty.textContent = emptyText;
      container.appendChild(empty);
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
      const citations = collectMessageCitations(message);
      appendUniqueCitations(renderedCitations, citations);
      const actions = normalizeMessageActions(message && message.actions, chatConfig && chatConfig.actions);
      if (actions.some((entry) => entry && entry.id === "expand") && fullText.length > 280) {
        setExpandedContent(content, fullText, false, citations);
      } else {
        setRenderedMessageContent(content, fullText, citations);
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
        renderStreamingContent(content, message, citations, () => revealMessageCitations(row));
      }
      renderMessageAttachments(bubble, message, chatConfig, { deferCitations: isStreamingMessage, citations: citations });
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
      renderMessageActions(bubble, actions, message, content, citations, handleAction);
      row.appendChild(bubble);
      container.appendChild(row);
    });
    maybeOpenCitationFromDeepLink(renderedCitations);
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
    const contract = new Map();
    if (Array.isArray(defaults)) {
      defaults.forEach((entry) => {
        const normalized = normalizeMessageActionEntry(entry);
        if (!normalized || contract.has(normalized.id)) return;
        contract.set(normalized.id, normalized);
      });
    }
    const values = Array.isArray(raw) ? raw : Array.from(contract.values());
    const normalized = [];
    const seen = new Set();
    values.forEach((entry) => {
      const next = normalizeMessageActionEntry(entry);
      if (!next || seen.has(next.id)) return;
      if (contract.size > 0 && !contract.has(next.id)) return;
      const configured = contract.get(next.id);
      if (configured && !next.label) next.label = configured.label;
      if (configured && !next.icon) next.icon = configured.icon;
      if (configured && !next.style) next.style = configured.style;
      if (configured && !next.action_id) next.action_id = configured.action_id;
      if (configured && !next.action_type) next.action_type = configured.action_type;
      if (configured && !next.flow) next.flow = configured.flow;
      if (configured && !next.target) next.target = configured.target;
      if (configured && (!next.payload || typeof next.payload !== "object")) next.payload = configured.payload;
      normalized.push(next);
      seen.add(next.id);
    });
    return normalized;
  }

  function normalizeMessageActionEntry(entry) {
    if (typeof entry === "string") {
      const id = entry.trim().toLowerCase();
      if (!id) return null;
      return { id: id, label: "", icon: "" };
    }
    if (!entry || typeof entry !== "object") return null;
    const rawId = typeof entry.id === "string" ? entry.id : typeof entry.action === "string" ? entry.action : "";
    const id = rawId.trim().toLowerCase();
    if (!id) return null;
    const label = typeof entry.label === "string" ? entry.label.trim() : "";
    const icon = typeof entry.icon === "string" ? entry.icon.trim().toLowerCase().replace(/[\s-]+/g, "_") : "";
    const style = normalizeMessageActionStyle(entry.style);
    const actionId = typeof entry.action_id === "string" ? entry.action_id.trim() : "";
    const actionType = typeof entry.action_type === "string" ? entry.action_type.trim() : "";
    const flow = typeof entry.flow === "string" ? entry.flow.trim() : "";
    const target = typeof entry.target === "string" ? entry.target.trim() : "";
    const payload =
      entry.payload && typeof entry.payload === "object" && !Array.isArray(entry.payload) ? { ...entry.payload } : null;
    return {
      id: id,
      label: label,
      icon: icon,
      style: style,
      action_id: actionId,
      action_type: actionType,
      flow: flow,
      target: target,
      payload: payload,
    };
  }

  function normalizeMessageActionStyle(value) {
    if (typeof value !== "string") return "";
    const style = value
      .trim()
      .toLowerCase()
      .replace(/[\s-]+/g, "_");
    if (style === "icon" || style === "icon_plain" || style === "text") {
      return style;
    }
    return "";
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
    const citations = Array.isArray(config.citations) ? config.citations : collectMessageCitations(message);
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

  function renderMessageActions(container, actions, message, contentNode, citations, handleAction) {
    if (!actions.length) return;
    const bar = document.createElement("div");
    bar.className = "ui-chat-message-actions";
    actions.forEach((actionEntry) => {
      const action = actionEntry && typeof actionEntry.id === "string" ? actionEntry.id : "";
      if (!action) return;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn small ghost ui-chat-message-action-btn";
      const label = actionEntry.label || defaultMessageActionLabel(action);
      setMessageActionVisual(button, { label: label, icon: actionEntry.icon || "", style: actionEntry.style || "" });
      const dispatch = resolveMessageActionDispatch(actionEntry, action);
      if (action === "copy") {
        button.onclick = async () => {
          const text = typeof message.content === "string" ? message.content : "";
          await copyToClipboard(text);
          button.dataset.state = "copied";
          button.title = "Copied";
          setTimeout(() => {
            button.dataset.state = "";
            button.title = label;
          }, 800);
        };
      } else if (action === "expand") {
        button.onclick = () => {
          const expanded = contentNode.dataset.expanded === "true";
          const fullText = typeof message.content === "string" ? message.content : contentNode.dataset.fullText || contentNode.textContent || "";
          setExpandedContent(contentNode, fullText, !expanded, citations);
          const nextLabel = expanded ? "Expand" : "Collapse";
          button.setAttribute("aria-label", nextLabel);
          button.title = nextLabel;
        };
      } else if (action === "view_sources") {
        button.onclick = () => {
          const messageCitations = Array.isArray(citations) ? citations : collectMessageCitations(message);
          if (!messageCitations.length) {
            button.dataset.state = "empty";
            button.title = "No sources";
            setTimeout(() => {
              button.dataset.state = "";
              button.title = label;
            }, 1000);
            return;
          }
          openCitationPreview(messageCitations[0], button, messageCitations);
        };
      } else if (dispatch && typeof handleAction === "function") {
        button.onclick = async () => {
          button.disabled = true;
          try {
            await handleAction(dispatch.action, dispatch.payload, button);
          } finally {
            button.disabled = false;
          }
        };
      } else {
        button.disabled = true;
        button.dataset.state = "unavailable";
        button.title = `${label} unavailable`;
      }
      bar.appendChild(button);
    });
    container.appendChild(bar);
  }

  function defaultMessageActionLabel(action) {
    if (typeof action !== "string" || !action) return "Action";
    const words = action
      .trim()
      .replace(/[\s\-]+/g, "_")
      .split("_")
      .filter(Boolean);
    if (!words.length) return "Action";
    return words.map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
  }

  function resolveMessageActionDispatch(actionEntry, fallbackActionId) {
    if (!actionEntry || typeof actionEntry !== "object") return null;
    const actionId = typeof actionEntry.action_id === "string" ? actionEntry.action_id.trim() : "";
    const actionType = typeof actionEntry.action_type === "string" ? actionEntry.action_type.trim() : "";
    const flow = typeof actionEntry.flow === "string" ? actionEntry.flow.trim() : "";
    const target = typeof actionEntry.target === "string" ? actionEntry.target.trim() : "";
    const payload =
      actionEntry.payload && typeof actionEntry.payload === "object" && !Array.isArray(actionEntry.payload)
        ? { ...actionEntry.payload }
        : {};
    if (!actionId && !actionType && !flow && !target && Object.keys(payload).length === 0) {
      return null;
    }
    const fallbackId = typeof fallbackActionId === "string" ? fallbackActionId.trim() : "";
    const resolvedId = actionId || fallbackId;
    if (!resolvedId) return null;
    const action = {
      id: resolvedId,
      type: actionType || "call_flow",
    };
    if (flow) action.flow = flow;
    if (target) action.target = target;
    return { action: action, payload: payload };
  }

  function setMessageActionVisual(button, config) {
    const label = config && typeof config.label === "string" ? config.label : "Action";
    const iconName = config && typeof config.icon === "string" ? config.icon : "";
    const style = normalizeMessageActionStyle(config && typeof config.style === "string" ? config.style : "");
    button.setAttribute("aria-label", label);
    button.title = label;
    if (iconName && style !== "text" && typeof root.createIconNode === "function") {
      button.classList.add("icon-button", "ui-chat-message-action-icon");
      if (style === "icon_plain") {
        button.classList.add("ui-chat-message-action-icon-plain");
      }
      const icon = root.createIconNode(iconName, { size: "small", decorative: true });
      button.textContent = "";
      button.appendChild(icon);
      return;
    }
    button.textContent = label;
  }

  function setExpandedContent(node, fullText, expanded, citations) {
    node.dataset.fullText = fullText;
    node.dataset.expanded = expanded ? "true" : "false";
    if (expanded || fullText.length <= 280) {
      setRenderedMessageContent(node, fullText, citations);
      return;
    }
    setRenderedMessageContent(node, `${fullText.slice(0, 280)}...`, citations);
  }

  function setRenderedMessageContent(node, text, citations) {
    renderInlineCitationText(node, typeof text === "string" ? text : "", citations);
  }

  function renderInlineCitationText(container, text, citations) {
    container.textContent = "";
    if (!text) return;
    if (!Array.isArray(citations) || !citations.length || text.indexOf("[") === -1) {
      container.textContent = text;
      return;
    }
    const markerPattern = /\[(\d{1,3})\]/g;
    let displayCounter = 0;
    let cursor = 0;
    let match = markerPattern.exec(text);
    while (match) {
      if (match.index > cursor) {
        container.appendChild(document.createTextNode(text.slice(cursor, match.index)));
      }
      const marker = Number.parseInt(match[1], 10);
      const citationEntry = resolveInlineCitationEntry(citations, marker);
      if (citationEntry) {
        displayCounter += 1;
        const button = document.createElement("button");
        button.type = "button";
        button.className = "ui-chat-inline-citation";
        button.textContent = String(displayCounter);
        button.title = citationEntry.title ? `Open source ${displayCounter}: ${citationEntry.title}` : `Open source ${displayCounter}`;
        if (typeof citationEntry.citation_id === "string" && citationEntry.citation_id) {
          button.dataset.citationId = citationEntry.citation_id;
        }
        button.onclick = () => {
          if (typeof citationEntry.citation_id === "string" && citationEntry.citation_id && typeof root.selectCitationId === "function") {
            root.selectCitationId(citationEntry.citation_id);
          }
          openCitationPreview(citationEntry, button, citations);
        };
        container.appendChild(button);
      } else {
        container.appendChild(document.createTextNode(match[0]));
      }
      cursor = markerPattern.lastIndex;
      match = markerPattern.exec(text);
    }
    if (cursor < text.length) {
      container.appendChild(document.createTextNode(text.slice(cursor)));
    }
  }

  function resolveInlineCitationEntry(citations, marker) {
    if (!Array.isArray(citations) || !citations.length) return null;
    if (!Number.isFinite(marker) || marker < 1) return null;
    for (const entry of citations) {
      const value = Number(entry && entry.index);
      if (Number.isFinite(value) && Math.max(1, Math.trunc(value)) === marker) {
        return entry;
      }
    }
    if (marker <= citations.length) return citations[marker - 1];
    return null;
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
    const direct = normalizeCitationEntries(message && message.citations);
    appendUniqueCitations(values, direct);
    const attachments = Array.isArray(message && message.attachments) ? message.attachments : [];
    attachments.forEach((attachment) => {
      if (!attachment || attachment.type !== "citation") return;
      appendUniqueCitations(values, normalizeCitationEntries([attachment]));
    });
    return values;
  }

  function appendUniqueCitations(target, entries) {
    if (!Array.isArray(target) || !Array.isArray(entries) || !entries.length) return;
    const seen = new Set(target.map((entry) => citationIdentity(entry)));
    entries.forEach((entry) => {
      const key = citationIdentity(entry);
      if (seen.has(key)) return;
      seen.add(key);
      target.push(entry);
    });
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

  function renderStreamingContent(contentNode, message, citations, onComplete) {
    const fullText = typeof message.content === "string" ? message.content : "";
    const tokenValues = Array.isArray(message.tokens)
      ? message.tokens.filter((entry) => typeof entry === "string")
      : fullText.split(/(\s+)/).filter((entry) => entry.length > 0);
    if (!tokenValues.length) {
      setRenderedMessageContent(contentNode, fullText, citations);
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
      setRenderedMessageContent(contentNode, fullText, citations);
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

  function formatUploadSize(value) {
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0) return "";
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  }

  function normalizeUploadSnapshotFile(file) {
    if (!file || typeof file !== "object") return null;
    const normalized = {};
    if (typeof file.id === "string" && file.id) normalized.id = file.id;
    if (typeof file.name === "string" && file.name) normalized.name = file.name;
    if (typeof file.type === "string" && file.type) normalized.type = file.type;
    if (typeof file.checksum === "string" && file.checksum) normalized.checksum = file.checksum;
    if (typeof file.size === "number" && Number.isFinite(file.size) && file.size >= 0) normalized.size = file.size;
    return normalized;
  }

  function normalizeUploadSnapshot(snapshot, fallbackName) {
    if (!snapshot || typeof snapshot !== "object") return null;
    const name = typeof snapshot.name === "string" && snapshot.name ? snapshot.name : fallbackName || "";
    const files = Array.isArray(snapshot.files)
      ? snapshot.files.map((entry) => normalizeUploadSnapshotFile(entry)).filter((entry) => entry && typeof entry === "object")
      : [];
    return {
      name: name,
      label: typeof snapshot.label === "string" ? snapshot.label : "",
      files: files,
      clear_action_id: typeof snapshot.clear_action_id === "string" ? snapshot.clear_action_id : "",
      action_id: typeof snapshot.action_id === "string" ? snapshot.action_id : "",
    };
  }

  function parseUploadSnapshotFromNode(uploadNode, uploadName) {
    if (!uploadNode || !uploadNode.dataset || !uploadNode.dataset.uploadState) return null;
    try {
      const parsed = JSON.parse(uploadNode.dataset.uploadState);
      return normalizeUploadSnapshot(parsed, uploadName);
    } catch (error) {
      return null;
    }
  }

  function findComposerUploadSnapshot(anchorNode, uploadName) {
    const key = typeof uploadName === "string" ? uploadName.trim() : "";
    if (!key) return null;
    if (typeof root.getUploadStateSnapshot === "function") {
      const snapshot = normalizeUploadSnapshot(root.getUploadStateSnapshot(key), key);
      if (snapshot) return snapshot;
    }
    const stateByName = root.__uploadStateByName && typeof root.__uploadStateByName === "object" ? root.__uploadStateByName : null;
    if (stateByName && stateByName[key]) {
      const snapshot = normalizeUploadSnapshot(stateByName[key], key);
      if (snapshot) return snapshot;
    }
    const uploadNode = findComposerUploadNode(anchorNode, key);
    const snapshot = parseUploadSnapshotFromNode(uploadNode, key);
    return snapshot || null;
  }

  function renderComposerUploadFiles(container, snapshot, handleAction) {
    if (!container) return;
    container.textContent = "";
    const normalized = normalizeUploadSnapshot(snapshot, "");
    const files = normalized && Array.isArray(normalized.files) ? normalized.files : [];
    if (!files.length) {
      container.classList.add("hidden");
      return;
    }
    container.classList.remove("hidden");
    const list = document.createElement("div");
    list.className = "ui-chat-composer-file-list";
    const clearActionId = normalized && typeof normalized.clear_action_id === "string" ? normalized.clear_action_id : "";
    files.forEach((file) => {
      const chip = document.createElement("div");
      chip.className = "ui-chat-composer-file-chip";
      const name = typeof file.name === "string" && file.name ? file.name : "File";
      const size = formatUploadSize(file.size);
      const text = document.createElement("span");
      text.className = "ui-chat-composer-file-name";
      text.textContent = size ? `${name} (${size})` : name;
      chip.appendChild(text);
      if (clearActionId) {
        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "ui-chat-composer-file-remove";
        removeButton.setAttribute("aria-label", `Remove ${name}`);
        removeButton.title = `Remove ${name}`;
        removeButton.textContent = "x";
        const uploadId =
          (typeof file.id === "string" && file.id) ||
          (typeof file.checksum === "string" && file.checksum) ||
          "";
        removeButton.onclick = async (event) => {
          event.preventDefault();
          removeButton.disabled = true;
          try {
            await handleAction(
              {
                id: clearActionId,
                type: "upload_clear",
              },
              uploadId ? { upload_id: uploadId } : {},
              event.currentTarget
            );
          } finally {
            removeButton.disabled = false;
          }
        };
        chip.appendChild(removeButton);
      }
      list.appendChild(chip);
    });
    container.appendChild(list);
    if (clearActionId && files.length > 1) {
      const clearAll = document.createElement("button");
      clearAll.type = "button";
      clearAll.className = "ui-chat-composer-file-clear";
      clearAll.textContent = "Clear";
      clearAll.onclick = async (event) => {
        event.preventDefault();
        clearAll.disabled = true;
        try {
          await handleAction(
            {
              id: clearActionId,
              type: "upload_clear",
            },
            {},
            event.currentTarget
          );
        } finally {
          clearAll.disabled = false;
        }
      };
      container.appendChild(clearAll);
    }
  }

  function renderComposer(child, handleAction, chatConfig) {
    const form = document.createElement("form");
    form.className = "ui-chat-composer";
    const composerSurface = document.createElement("div");
    composerSurface.className = "ui-chat-composer-surface";
    form.appendChild(composerSurface);
    const composerFiles = document.createElement("div");
    composerFiles.className = "ui-chat-composer-files hidden";
    form.appendChild(composerFiles);
    const composerPlaceholder =
      chatConfig && typeof chatConfig.composer_placeholder === "string" && chatConfig.composer_placeholder.trim()
        ? chatConfig.composer_placeholder.trim()
        : "Ask about your documents... use #project or @document";
    const composerSendStyle =
      chatConfig && typeof chatConfig.composer_send_style === "string" && chatConfig.composer_send_style.trim()
        ? chatConfig.composer_send_style.trim().toLowerCase()
        : "icon";
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
    const composerAttachUpload =
      chatConfig && typeof chatConfig.composer_attach_upload === "string" ? chatConfig.composer_attach_upload.trim() : "";
    const fields = normalizeComposerFields(child);
    const inputs = new Map();
    let messageInput = null;
    let refreshComposerFiles = null;
    const attachmentsEnabled = Boolean(chatConfig && chatConfig.attachments);
    if (attachmentsEnabled && composerAttachUpload) {
      registerComposerAttachUpload(composerAttachUpload);
      hideComposerUploadSurface(document, composerAttachUpload);
      window.setTimeout(() => {
        hideComposerUploadSurface(form, composerAttachUpload);
      }, 0);
      refreshComposerFiles = () => {
        const snapshot = findComposerUploadSnapshot(form, composerAttachUpload);
        renderComposerUploadFiles(composerFiles, snapshot, handleAction);
      };
      refreshComposerFiles();
      const attachButton = document.createElement("button");
      attachButton.type = "button";
      attachButton.className = "ui-chat-composer-attach";
      attachButton.setAttribute("aria-label", "Attach files");
      attachButton.title = "Attach files";
      if (typeof root.createIconNode === "function") {
        const icon = root.createIconNode("add", { size: "small", decorative: true });
        attachButton.appendChild(icon);
      } else {
        attachButton.textContent = "+";
      }
      attachButton.onclick = (event) => {
        event.preventDefault();
        event.stopPropagation();
        const uploadInput = findComposerUploadInput(form, composerAttachUpload);
        if (uploadInput && uploadInput.disabled !== true) {
          uploadInput.__n3UploadPickerPostAction = null;
          const openPicker = typeof root.openUploadInputPicker === "function" ? root.openUploadInputPicker : null;
          if (openPicker) {
            openPicker(uploadInput);
          } else {
            uploadInput.click();
          }
        }
      };
      composerSurface.appendChild(attachButton);
      window.setTimeout(() => {
        if (typeof refreshComposerFiles === "function") refreshComposerFiles();
      }, 0);
    }
    fields.forEach((field) => {
      const name = field.name || "message";
      const placeholder = name === "message" ? composerPlaceholder : String(name);
      const input = name === "message" ? document.createElement("textarea") : document.createElement("input");
      if (input.tagName.toLowerCase() === "input") {
        input.type = "text";
      } else {
        input.className = "ui-chat-composer-message";
        input.rows = 1;
        input.addEventListener("keydown", (event) => {
          if (event.key !== "Enter" || event.shiftKey) return;
          if (event.currentTarget && event.currentTarget.dataset && event.currentTarget.dataset.mentionMenuOpen === "true") {
            return;
          }
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
      composerSurface.appendChild(input);
      if (name === "message") {
        messageInput = input;
      }
    });
    const mentionController = messageInput ? setupComposerMentions(composerSurface, messageInput) : null;
    const advancedControls = actionType === "chat.message.send" ? buildComposerAdvancedControls(composerState) : null;
    if (advancedControls) {
      form.appendChild(advancedControls.node);
    }
    const button = document.createElement("button");
    button.type = "submit";
    button.className = "btn small ui-chat-composer-send";
    button.setAttribute("aria-label", "Send message");
    if (composerSendStyle === "text") {
      button.textContent = "Send";
    } else if (typeof root.createIconNode === "function") {
      const icon = root.createIconNode("send", { size: "small", decorative: true });
      icon.classList.add("ui-chat-composer-send-icon");
      button.appendChild(icon);
    } else {
      button.textContent = "↑";
    }
    composerSurface.appendChild(button);

    const updateSubmitState = () => {
      const value = messageInput && typeof messageInput.value === "string" ? messageInput.value.trim() : "";
      const enabled = value.length > 0;
      button.disabled = !enabled;
      button.classList.toggle("is-active", enabled);
    };
    if (messageInput) {
      messageInput.addEventListener("input", updateSubmitState);
    }
    updateSubmitState();

    composerSurface.addEventListener("click", (event) => {
      if (event.target && event.target.closest && event.target.closest("button, input, textarea, select, a, label")) return;
      if (messageInput && typeof messageInput.focus === "function") {
        messageInput.focus();
      }
    });

    form.onsubmit = async (e) => {
      e.preventDefault();
      updateSubmitState();
      if (button.disabled) return;
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
      if (mentionController) {
        const messageValue = typeof payload.message === "string" ? payload.message : "";
        const mentionPayload = mentionController.buildPayload(messageValue);
        payload.query_text = mentionPayload.queryText;
        payload.project_scope = mentionPayload.projectScope;
        payload.project_scope_label = mentionPayload.projectScopeLabel;
        payload.project_scope_conflict = mentionPayload.projectScopeConflict;
        payload.document_scope = mentionPayload.documentScope;
        payload.document_scope_mode = mentionPayload.documentScopeMode;
      }
      button.classList.add("is-sending");
      inputs.forEach((input) => {
        if (input) input.value = "";
      });
      const action = { id: child.action_id, type: actionType };
      if (actionFlow) {
        action.flow = actionFlow;
      }
      try {
        await handleAction(
          action,
          payload,
          button
        );
      } finally {
        button.classList.remove("is-sending");
        updateSubmitState();
      }
      if (messageInput && typeof messageInput.focus === "function") {
        messageInput.focus();
      }
      if (typeof refreshComposerFiles === "function") {
        refreshComposerFiles();
      }
    };
    return form;
  }

  function hideComposerUploadSurface(anchorNode, uploadName) {
    const input = findComposerUploadInput(anchorNode, uploadName);
    if (!input || typeof input.closest !== "function") return false;
    const wrapper = input.closest(".ui-upload");
    if (!wrapper || !wrapper.classList) return false;
    wrapper.classList.add("ui-upload-hidden-surface");
    return true;
  }

  function registerComposerAttachUpload(uploadName) {
    const key = typeof uploadName === "string" ? uploadName.trim() : "";
    if (!key) return;
    const registry =
      root.__hiddenComposerUploads && typeof root.__hiddenComposerUploads === "object"
        ? root.__hiddenComposerUploads
        : {};
    registry[key] = true;
    root.__hiddenComposerUploads = registry;
    if (root.__manifestComposerUploads && typeof root.__manifestComposerUploads === "object") {
      root.__manifestComposerUploads[key] = true;
    }
    if (typeof root.refreshUploadVisibility === "function") {
      root.refreshUploadVisibility(document);
    }
  }

  function findComposerUploadNode(anchorNode, uploadName) {
    const target = typeof uploadName === "string" ? uploadName.trim() : "";
    if (!target) return null;
    const roots = [];
    if (anchorNode && typeof anchorNode.closest === "function") {
      const sectionRoot = anchorNode.closest(".ui-section");
      if (sectionRoot) roots.push(sectionRoot);
    }
    if (anchorNode && typeof anchorNode.querySelectorAll === "function") {
      roots.push(anchorNode);
    }
    roots.push(document);
    const visited = new Set();
    for (const rootNode of roots) {
      if (!rootNode || typeof rootNode.querySelectorAll !== "function" || visited.has(rootNode)) continue;
      visited.add(rootNode);
      const uploads = rootNode.querySelectorAll(".ui-upload[data-upload-name]");
      for (const upload of uploads) {
        const currentName = upload && upload.dataset ? String(upload.dataset.uploadName || "").trim() : "";
        if (currentName === target) return upload;
      }
    }
    return null;
  }

  function findComposerUploadInput(anchorNode, uploadName) {
    const uploadNode = findComposerUploadNode(anchorNode, uploadName);
    if (!uploadNode || typeof uploadNode.querySelector !== "function") return null;
    const input = uploadNode.querySelector(".ui-upload-input");
    if (input && input.tagName && input.tagName.toLowerCase() === "input") {
      return input;
    }
    return null;
  }

  function setupComposerMentions(container, messageInput) {
    const mentionSources = collectMentionSources();
    if (!mentionSources.projects.length && !mentionSources.documents.length) {
      return null;
    }
    const state = {
      project: null,
      documents: [],
      activeSymbol: "",
      activeToken: "",
      options: [],
      activeIndex: 0,
    };

    const chips = document.createElement("div");
    chips.className = "ui-chat-mention-chips";
    const menu = document.createElement("div");
    menu.className = "ui-chat-mention-menu hidden";
    menu.setAttribute("role", "listbox");
    container.appendChild(chips);
    container.appendChild(menu);

    function clearMenu() {
      state.activeSymbol = "";
      state.activeToken = "";
      state.options = [];
      state.activeIndex = 0;
      menu.classList.add("hidden");
      menu.textContent = "";
      messageInput.dataset.mentionMenuOpen = "false";
    }

    function addDocumentChip(option) {
      if (!option || !option.id) return;
      const alreadySelected = state.documents.some((entry) => entry.id === option.id);
      if (alreadySelected) return;
      state.documents.push(option);
    }

    function addProjectChip(option) {
      if (!option || !option.id) return;
      state.project = option;
    }

    function removeTokenAtCaret(symbol, token) {
      const text = String(messageInput.value || "");
      const caret = Number.isInteger(messageInput.selectionStart) ? messageInput.selectionStart : text.length;
      const before = text.slice(0, caret);
      const after = text.slice(caret);
      const escapedSymbol = symbol === "#" ? "\\#" : "@";
      const pattern = new RegExp(`(^|\\s)(${escapedSymbol}${escapeRegex(token)})$`);
      const match = before.match(pattern);
      if (!match) return;
      const prefix = match[1] || "";
      const replacementStart = before.length - match[0].length + prefix.length;
      const nextBefore = `${before.slice(0, replacementStart)} `;
      const nextValue = `${nextBefore}${after}`.replace(/\s+/g, " ").replace(/\s+$/, "");
      messageInput.value = nextValue;
      const nextCaret = Math.min(nextBefore.length, messageInput.value.length);
      messageInput.setSelectionRange(nextCaret, nextCaret);
    }

    function renderChips() {
      chips.textContent = "";
      const renderChip = (kind, entry) => {
        const chip = document.createElement("span");
        chip.className = `ui-chat-mention-chip kind-${kind}`;
        if (typeof root.createIconNode === "function") {
          const icon = root.createIconNode(kind === "project" ? "folder_info" : "file", {
            size: "xsmall",
            decorative: true,
          });
          icon.classList.add("ui-chat-mention-chip-icon");
          chip.appendChild(icon);
        }
        const label = document.createElement("span");
        label.className = "ui-chat-mention-chip-label";
        label.textContent = `${kind === "project" ? "#" : "@"}${entry.label}`;
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "ui-chat-mention-chip-remove";
        remove.textContent = "×";
        remove.setAttribute("aria-label", `Remove ${kind} ${entry.label}`);
        remove.onclick = () => {
          if (kind === "project") {
            state.project = null;
          } else {
            state.documents = state.documents.filter((doc) => doc.id !== entry.id);
          }
          renderChips();
        };
        chip.appendChild(label);
        chip.appendChild(remove);
        chips.appendChild(chip);
      };

      if (state.project) {
        renderChip("project", state.project);
      }
      state.documents.forEach((entry) => renderChip("document", entry));
    }

    function renderMenu() {
      menu.textContent = "";
      if (!state.options.length) {
        clearMenu();
        return;
      }
      let lastGroup = "";
      state.options.forEach((option, index) => {
        const optionGroup = typeof option.group === "string" ? option.group : "";
        if (optionGroup && optionGroup !== lastGroup) {
          const heading = document.createElement("div");
          heading.className = "ui-chat-mention-group";
          heading.textContent = optionGroup;
          menu.appendChild(heading);
          lastGroup = optionGroup;
        }
        const item = document.createElement("button");
        item.type = "button";
        item.className = "ui-chat-mention-option";
        if (index === state.activeIndex) {
          item.classList.add("active");
        }
        if (typeof root.createIconNode === "function") {
          const icon = root.createIconNode(option.kind === "project" ? "folder_info" : "file", {
            size: "xsmall",
            decorative: true,
          });
          icon.classList.add("ui-chat-mention-option-icon");
          item.appendChild(icon);
        }
        const label = document.createElement("span");
        label.className = "ui-chat-mention-option-label";
        label.textContent = `${option.kind === "project" ? "#" : "@"}${option.label}`;
        item.appendChild(label);
        item.addEventListener("mousedown", (event) => {
          event.preventDefault();
        });
        item.onclick = () => {
          if (option.kind === "project") {
            addProjectChip(option);
          } else {
            addDocumentChip(option);
          }
          removeTokenAtCaret(state.activeSymbol, state.activeToken);
          renderChips();
          clearMenu();
          messageInput.focus();
        };
        menu.appendChild(item);
      });
      menu.classList.remove("hidden");
      messageInput.dataset.mentionMenuOpen = "true";
    }

    function updateSuggestions() {
      const text = String(messageInput.value || "");
      const caret = Number.isInteger(messageInput.selectionStart) ? messageInput.selectionStart : text.length;
      const before = text.slice(0, caret);
      const mentionMatch = before.match(/(^|\s)([#@])([A-Za-z0-9._-]*)$/);
      if (!mentionMatch) {
        clearMenu();
        return;
      }
      const symbol = mentionMatch[2];
      const token = mentionMatch[3] || "";
      const query = token.toLowerCase();
      const options =
        symbol === "#"
          ? mentionSources.projects
              .filter((entry) => entry.search.includes(query))
              .map((entry) => ({ kind: "project", id: entry.id, label: entry.label, search: entry.search, group: "Projects" }))
          : mentionSources.documents
              .filter((entry) => entry.search.includes(query))
              .map((entry) => ({
                kind: "document",
                id: entry.id,
                label: entry.label,
                search: entry.search,
                group: entry.group || "Documents",
              }));
      state.activeSymbol = symbol;
      state.activeToken = token;
      state.options = options.slice(0, 8);
      state.activeIndex = 0;
      renderMenu();
    }

    function selectActiveOption() {
      if (!state.options.length) return false;
      const option = state.options[Math.max(0, Math.min(state.activeIndex, state.options.length - 1))];
      if (!option) return false;
      if (option.kind === "project") {
        addProjectChip(option);
      } else {
        addDocumentChip(option);
      }
      removeTokenAtCaret(state.activeSymbol, state.activeToken);
      renderChips();
      clearMenu();
      return true;
    }

    messageInput.addEventListener("input", () => updateSuggestions());
    messageInput.addEventListener("click", () => updateSuggestions());
    messageInput.addEventListener("blur", () => {
      window.setTimeout(() => clearMenu(), 120);
    });
    messageInput.addEventListener("keydown", (event) => {
      if (menu.classList.contains("hidden")) return;
      if (event.key === "ArrowDown") {
        event.preventDefault();
        state.activeIndex = (state.activeIndex + 1) % state.options.length;
        renderMenu();
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        state.activeIndex = (state.activeIndex - 1 + state.options.length) % state.options.length;
        renderMenu();
        return;
      }
      if (event.key === "Enter" && !event.shiftKey) {
        if (selectActiveOption()) {
          event.preventDefault();
        }
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        clearMenu();
      }
    });

    renderChips();

    function resolveDocumentScopeMode(projectScopeId, projectScopeLabel, documentIds) {
      if (!Array.isArray(documentIds) || !documentIds.length) return "once";
      const activeProjectId = mentionSources.activeProjectId || "";
      const effectiveProjectId = projectScopeId || activeProjectId;
      const outsideDocuments = [];
      documentIds.forEach((docId) => {
        const entry = mentionSources.documentById.get(String(docId));
        const isInProject = Boolean(entry && entry.inProject && (!entry.projectId || entry.projectId === effectiveProjectId));
        if (!isInProject) outsideDocuments.push(entry || { id: docId, label: String(docId) });
      });
      if (!outsideDocuments.length) return "once";
      const label = projectScopeLabel || mentionSources.activeProjectLabel || "this project";
      const docLabel =
        outsideDocuments.length === 1
          ? outsideDocuments[0].label
          : `${outsideDocuments[0].label} and ${outsideDocuments.length - 1} more`;
      const confirmMessage = `Add ${docLabel} to ${label} for future chats?\nOK = Add & continue\nCancel = Use once`;
      const shouldAdd = window.confirm(confirmMessage);
      return shouldAdd ? "add" : "once";
    }

    return {
      buildPayload: (messageValue) => {
        const inline = extractInlineMentionScopes(String(messageValue || ""), mentionSources);
        const projectCandidates = [];
        if (state.project && state.project.id) {
          projectCandidates.push({ id: state.project.id, label: state.project.label });
        }
        inline.projectMentions.forEach((entry) => {
          const exists = projectCandidates.some((candidate) => candidate.id === entry.id);
          if (!exists) projectCandidates.push(entry);
        });
        const documentCandidates = [];
        state.documents.forEach((entry) => {
          if (!entry || !entry.id) return;
          if (!documentCandidates.includes(entry.id)) documentCandidates.push(entry.id);
        });
        inline.documentMentions.forEach((entry) => {
          if (!documentCandidates.includes(entry.id)) documentCandidates.push(entry.id);
        });
        const scopeConflict = projectCandidates.length > 1;
        const projectScope = scopeConflict ? "" : projectCandidates.length ? projectCandidates[0].id : "";
        const projectScopeLabel = scopeConflict ? "" : projectCandidates.length ? projectCandidates[0].label : "";
        const documentScopeMode = resolveDocumentScopeMode(projectScope, projectScopeLabel, documentCandidates);
        return {
          queryText: inline.queryText,
          projectScope: projectScope,
          projectScopeLabel: projectScopeLabel,
          projectScopeConflict: scopeConflict,
          documentScope: documentCandidates,
          documentScopeMode: documentScopeMode,
        };
      },
    };
  }

  function collectMentionSources() {
    const rowsByRecord = root.__listRowsByRecord && typeof root.__listRowsByRecord === "object" ? root.__listRowsByRecord : {};
    const entries = [];
    Object.entries(rowsByRecord).forEach(([recordName, rows]) => {
      if (!Array.isArray(rows)) return;
      rows.forEach((row) => {
        if (!row || typeof row !== "object") return;
        entries.push({ recordName: String(recordName || ""), row: row });
      });
    });

    const projectsById = new Map();
    let activeProjectId = "";
    let activeProjectLabel = "";

    entries.forEach(({ recordName, row }) => {
      const recordKey = recordName.toLowerCase();
      const id = textValue(row.project_id) || textValue(row.projectId) || textValue(row.id);
      const label = textValue(row.project_name) || textValue(row.projectName) || textValue(row.name) || textValue(row.label) || id;
      const hasDocumentFields = Boolean(
        textValue(row.upload_id) ||
          textValue(row.uploadId) ||
          textValue(row.document_id) ||
          textValue(row.documentId) ||
          textValue(row.source_name) ||
          textValue(row.sourceName) ||
          textValue(row.file_name) ||
          textValue(row.filename)
      );
      const recordLooksProject = /project/.test(recordKey) && !/knowledge|document|library|file/.test(recordKey);
      const rowLooksProject = Boolean(id && label && !hasDocumentFields);
      if (!recordLooksProject && !rowLooksProject) return;
      if (!id || !label) return;
      if (!projectsById.has(id)) {
        projectsById.set(id, {
          id: id,
          label: label,
          search: `${label.toLowerCase()} ${id.toLowerCase()} ${slugifyMentionToken(label)}`.trim(),
        });
      }
      if (row.active === true || row.is_active === true || row.selected === true || row.current === true) {
        activeProjectId = id;
        activeProjectLabel = label;
      }
    });

    const documentById = new Map();
    entries.forEach(({ recordName, row }) => {
      const recordKey = recordName.toLowerCase();
      const id =
        textValue(row.upload_id) ||
        textValue(row.uploadId) ||
        textValue(row.document_id) ||
        textValue(row.documentId) ||
        textValue(row.id);
      const label =
        textValue(row.source_name) ||
        textValue(row.sourceName) ||
        textValue(row.file_name) ||
        textValue(row.filename) ||
        textValue(row.title) ||
        id;
      const rowProjectId = textValue(row.project_id) || textValue(row.projectId);
      const hasDocumentFields = Boolean(
        textValue(row.upload_id) ||
          textValue(row.uploadId) ||
          textValue(row.document_id) ||
          textValue(row.documentId) ||
          textValue(row.source_name) ||
          textValue(row.sourceName) ||
          textValue(row.file_name) ||
          textValue(row.filename) ||
          textValue(row.title)
      );
      const recordLooksDocument = /knowledge|document|library|file/.test(recordKey);
      if (!id || !label) return;
      if (!recordLooksDocument && !hasDocumentFields) return;

      let inProject = false;
      if (typeof row.in_active_project === "boolean") {
        inProject = row.in_active_project;
      } else if (typeof row.in_project === "boolean") {
        inProject = row.in_project;
      } else if (rowProjectId) {
        inProject = activeProjectId ? rowProjectId === activeProjectId : true;
      }
      const projectId = rowProjectId || activeProjectId;
      const entry = {
        id: id,
        label: label,
        search: `${label.toLowerCase()} ${id.toLowerCase()} ${slugifyMentionToken(label)}`.trim(),
        group: inProject ? "In this project" : "From library",
        inProject: Boolean(inProject),
        projectId: projectId,
      };
      const existing = documentById.get(id);
      if (!existing || (!existing.inProject && entry.inProject)) {
        documentById.set(id, entry);
      }
    });

    const projects = Array.from(projectsById.values());
    if (!activeProjectId && projects.length === 1) {
      activeProjectId = projects[0].id;
      activeProjectLabel = projects[0].label;
    } else if (activeProjectId && !activeProjectLabel) {
      const active = projectsById.get(activeProjectId);
      if (active) activeProjectLabel = active.label;
    }
    const documents = Array.from(documentById.values()).sort((left, right) => {
      if (left.inProject !== right.inProject) return left.inProject ? -1 : 1;
      return left.label.localeCompare(right.label);
    });

    return { projects, documents, activeProjectId, activeProjectLabel, documentById };
  }

  function extractInlineMentionScopes(messageText, mentionSources) {
    const text = typeof messageText === "string" ? messageText : "";
    const projectMentions = [];
    const documentMentions = [];
    const projectTokenPattern = /(^|\s)#([A-Za-z0-9._-]+)/g;
    const documentTokenPattern = /(^|\s)@([A-Za-z0-9._-]+)/g;

    let projectMatch = projectTokenPattern.exec(text);
    while (projectMatch) {
      const token = projectMatch[2];
      const resolved = resolveMentionToken(token, mentionSources.projects);
      if (resolved && !projectMentions.some((entry) => entry.id === resolved.id)) {
        projectMentions.push(resolved);
      }
      projectMatch = projectTokenPattern.exec(text);
    }

    let documentMatch = documentTokenPattern.exec(text);
    while (documentMatch) {
      const token = documentMatch[2];
      const resolved = resolveMentionToken(token, mentionSources.documents);
      if (resolved && !documentMentions.some((entry) => entry.id === resolved.id)) {
        documentMentions.push(resolved);
      }
      documentMatch = documentTokenPattern.exec(text);
    }

    const queryText = text
      .replace(projectTokenPattern, "$1")
      .replace(documentTokenPattern, "$1")
      .replace(/\s+/g, " ")
      .trim();

    return {
      queryText: queryText,
      projectMentions: projectMentions,
      documentMentions: documentMentions,
    };
  }

  function resolveMentionToken(token, sourceRows) {
    const needle = typeof token === "string" ? token.trim().toLowerCase() : "";
    if (!needle) return null;
    const byId = sourceRows.find((entry) => entry.id.toLowerCase() === needle);
    if (byId) return { id: byId.id, label: byId.label };
    const bySlug = sourceRows.find((entry) => slugifyMentionToken(entry.label) === needle);
    if (bySlug) return { id: bySlug.id, label: bySlug.label };
    return null;
  }

  function slugifyMentionToken(value) {
    const text = textValue(value);
    if (!text) return "";
    return text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function escapeRegex(value) {
    return String(value || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
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
    const citationId = textValue(entry.citation_id) || null;
    const sourceId = textValue(entry.source_id);
    const chunkId = textValue(entry.chunk_id) || sourceId || null;
    const previewUrl = textValue(entry.preview_url) || textValue(entry.url);
    const urlTarget = parsePreviewTargetFromUrl(previewUrl);
    if (urlTarget && urlTarget.documentId && urlTarget.pageNumber) {
      return {
        documentId: urlTarget.documentId,
        pageNumber: urlTarget.pageNumber,
        chunkId: urlTarget.chunkId || chunkId,
        citationId: urlTarget.citationId || citationId,
      };
    }
    const deepLinkTarget = parsePreviewTargetFromDeepLink(textValue(entry.deep_link_query));
    if (deepLinkTarget && deepLinkTarget.documentId && deepLinkTarget.pageNumber) {
      return {
        documentId: deepLinkTarget.documentId,
        pageNumber: deepLinkTarget.pageNumber,
        chunkId: deepLinkTarget.chunkId || chunkId,
        citationId: deepLinkTarget.citationId || citationId,
      };
    }
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
    if (!documentId && looksLikeDocumentId(sourceId)) {
      documentId = sourceId;
    }
    const resolvedPageNumber = pageNumber || (documentId ? 1 : null);
    if (documentId && resolvedPageNumber) {
      return { documentId: documentId, pageNumber: resolvedPageNumber, chunkId: chunkId, citationId: citationId };
    }
    return null;
  }

  function looksLikeDocumentId(value) {
    const text = textValue(value);
    if (!text) return false;
    if (/^[a-f0-9]{24,}$/i.test(text)) return true;
    if (/^[A-Za-z0-9_-]{32,}$/.test(text)) return true;
    return false;
  }

  function parsePreviewTargetFromUrl(urlValue) {
    const text = textValue(urlValue);
    if (!text) return null;
    let parsed;
    try {
      parsed = new URL(text, window.location.origin);
    } catch (_err) {
      return null;
    }
    const chunkId = textValue(parsed.searchParams.get("chunk_id")) || null;
    const citationId =
      textValue(parsed.searchParams.get("citation_id")) || textValue(parsed.searchParams.get("cit")) || null;
    const pathMatch = parsed.pathname.match(/^\/api\/documents\/([^/]+)\/pages\/(\d+)$/);
    if (pathMatch) {
      const documentId = decodeURIComponent(pathMatch[1] || "");
      const pageNumber = toPageNumber(pathMatch[2]);
      if (!documentId || !pageNumber) return null;
      return {
        documentId: documentId,
        pageNumber: pageNumber,
        chunkId: chunkId,
        citationId: citationId,
      };
    }
    const pdfMatch = parsed.pathname.match(/^\/api\/documents\/([^/]+)\/pdf$/);
    if (!pdfMatch) return null;
    const documentId = decodeURIComponent(pdfMatch[1] || "");
    const hashQuery = parsed.hash.startsWith("#") ? parsed.hash.slice(1) : parsed.hash;
    const hashParams = new URLSearchParams(hashQuery);
    const pageNumber = toPageNumber(hashParams.get("page")) || toPageNumber(parsed.searchParams.get("page"));
    if (!documentId || !pageNumber) return null;
    const hashCitationId =
      textValue(hashParams.get("citation_id")) || textValue(hashParams.get("cit")) || textValue(hashParams.get("n3_cit"));
    return {
      documentId: documentId,
      pageNumber: pageNumber,
      chunkId: chunkId,
      citationId: hashCitationId || citationId,
    };
  }

  function parsePreviewTargetFromDeepLink(queryValue) {
    const text = textValue(queryValue);
    if (!text) return null;
    const query = text.startsWith("?") ? text.slice(1) : text;
    const params = new URLSearchParams(query);
    const documentId = textValue(params.get("n3_doc")) || textValue(params.get("doc"));
    const pageText =
      textValue(params.get("n3_doc_page")) || textValue(params.get("doc_page")) || textValue(params.get("n3_page"));
    let pageNumber = toPageNumber(pageText);
    if (!pageNumber && documentId) {
      const legacyPageText = textValue(params.get("page"));
      if (/^\d+$/.test(legacyPageText)) {
        pageNumber = toPageNumber(legacyPageText);
      }
    }
    const citationId =
      textValue(params.get("n3_cit")) || textValue(params.get("citation_id")) || textValue(params.get("cit")) || null;
    const chunkId = textValue(params.get("n3_chunk")) || textValue(params.get("chunk_id")) || null;
    if (!documentId || !pageNumber) return null;
    return {
      chunkId: chunkId,
      documentId: documentId,
      pageNumber: pageNumber,
      citationId: citationId,
    };
  }

  function buildCitationPdfPreviewUrl(config) {
    const options = config && typeof config === "object" ? config : {};
    const documentId = textValue(options.documentId);
    const pageNumber = toPageNumber(options.pageNumber) || 1;
    const baseUrl = textValue(options.baseUrl);
    const fallbackBase = documentId ? `/api/documents/${encodeURIComponent(documentId)}/pdf` : "/api/documents/unknown/pdf";
    const resolvedBase = baseUrl || `${fallbackBase}#page=${pageNumber}`;
    const hashIndex = resolvedBase.indexOf("#");
    const urlBase = hashIndex >= 0 ? resolvedBase.slice(0, hashIndex) : resolvedBase;
    const hash = hashIndex >= 0 ? resolvedBase.slice(hashIndex + 1) : "";
    const params = new URLSearchParams(hash);
    if (!params.get("page")) params.set("page", String(pageNumber));
    const searchTerm = buildCitationSearchQuery(options.snippet);
    if (searchTerm && !params.get("search")) {
      params.set("search", searchTerm);
    }
    return `${urlBase}#${params.toString()}`;
  }

  function buildCitationSearchQuery(snippet) {
    const text = textValue(snippet);
    if (!text) return "";
    const normalized = text
      .replace(/\[[0-9]{1,3}\]/g, " ")
      .replace(/[^A-Za-z0-9\s-]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
    if (!normalized) return "";
    const words = normalized.split(" ").filter((word) => word.length > 1);
    if (!words.length) return "";
    const phrase = words.slice(0, 14).join(" ");
    return phrase.length > 140 ? `${phrase.slice(0, 140).trim()}` : phrase;
  }

  function sanitizeHighlightColor(value) {
    const text = textValue(value);
    if (!text) return "";
    if (/^#[0-9a-f]{3,8}$/i.test(text)) return text;
    if (/^(rgb|rgba|hsl|hsla)\(/i.test(text)) return text;
    if (/^[A-Za-z]+$/.test(text)) return text;
    return "";
  }

  function resolveCitationHighlightColor(entry) {
    if (!entry || typeof entry !== "object") return "";
    return (
      sanitizeHighlightColor(entry.highlight_color) ||
      sanitizeHighlightColor(entry.highlightColor) ||
      sanitizeHighlightColor(entry.color) ||
      sanitizeHighlightColor(entry.color_hex) ||
      sanitizeHighlightColor(entry.hex_color)
    );
  }

  function textValue(value) {
    if (typeof value !== "string") return "";
    const trimmed = value.trim();
    return trimmed ? trimmed : "";
  }

  function toPageNumber(value) {
    if (typeof value === "number" && Number.isFinite(value)) {
      const parsed = Math.trunc(value);
      return parsed > 0 ? parsed : null;
    }
    if (typeof value === "string" && value.trim()) {
      const trimmed = value.trim();
      if (/^\d+$/.test(trimmed)) {
        const parsed = Number.parseInt(trimmed, 10);
        if (!Number.isNaN(parsed) && parsed > 0) return parsed;
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

  function renderNoSourcesPanel(container) {
    if (!(container instanceof HTMLElement)) return;
    const panel = document.createElement("div");
    panel.className = "ui-empty-sources-panel";
    const message = document.createElement("div");
    message.textContent = "No sources available yet.";
    const actions = document.createElement("div");
    actions.className = "ui-empty-sources-actions";
    const uploadButton = document.createElement("button");
    uploadButton.type = "button";
    uploadButton.className = "btn small";
    uploadButton.textContent = "Upload document";
    actions.appendChild(uploadButton);
    panel.appendChild(message);
    panel.appendChild(actions);
    container.appendChild(panel);
  }

  function renderPreviewSources(citations, selectedIndex) {
    const preview = ensureCitationPreview();
    preview.sourcesList.textContent = "";
    preview.sourceItems = [];
    if (!Array.isArray(citations) || !citations.length) {
      renderNoSourcesPanel(preview.sourcesList);
      return;
    }
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
      } else if (citationDisplayUrl(entry.url)) {
        meta.textContent = "Source link available";
      } else if (citationDisplaySource(entry.source_id)) {
        meta.textContent = citationDisplaySource(entry.source_id);
      } else if (entry.source_id) {
        meta.textContent = "Source available";
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
    preview.highlightColor = resolveCitationHighlightColor(entry);
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
      preview.citationId =
        (typeof target.citationId === "string" && target.citationId) ||
        (typeof entry.citation_id === "string" ? entry.citation_id : null);
      preview.lastDeepLinkKey = `${target.documentId}|${target.pageNumber}|${preview.citationId || ""}|${preview.chunkId || ""}`;
      loadPreviewPage(target.documentId, target.pageNumber, preview.chunkId, preview.citationId);
      if (typeof root.applyCitationDeepLinkState === "function") {
        root.applyCitationDeepLinkState({
          citation_id: preview.citationId || "",
          chunk_id: preview.chunkId || "",
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
    const hasPreviewTarget = Boolean(resolveCitationTarget(citations[selectedIndex]));
    selectPreviewCitation(selectedIndex, { openPreviewTab: hasPreviewTarget });
    preview.container.classList.remove("hidden");
    preview.container.setAttribute("aria-hidden", "false");
    if (hasPreviewTarget) {
      setCitationPreviewTab("preview");
    } else {
      setCitationPreviewTab("sources");
    }
    preview.panel.focus();
  }

  function maybeOpenCitationFromDeepLink(citations) {
    if (!Array.isArray(citations) || !citations.length) return;
    if (typeof root.parseCitationDeepLink !== "function") return;
    const deepLink = root.parseCitationDeepLink(window.location.search || "");
    if (!deepLink || typeof deepLink !== "object") return;
    const documentId = textValue(deepLink.document_id || deepLink.documentId);
    const citationId = textValue(deepLink.citation_id || deepLink.citationId);
    const chunkId = textValue(deepLink.chunk_id || deepLink.chunkId);
    const pageNumber = toPageNumber(deepLink.page_number || deepLink.page);
    if (!documentId && !citationId) return;
    const deepLinkKey = `${documentId}|${pageNumber || ""}|${citationId}|${chunkId}`;
    if (!deepLinkKey || previewState.lastDeepLinkKey === deepLinkKey) return;
    let selected = null;
    if (citationId) {
      selected = citations.find((entry) => {
        if (!entry || typeof entry.citation_id !== "string" || entry.citation_id.trim() !== citationId) return false;
        const target = resolveCitationTarget(entry);
        if (!target) return false;
        if (documentId && target.documentId !== documentId) return false;
        if (pageNumber && target.pageNumber !== pageNumber) return false;
        if (chunkId && textValue(target.chunkId) !== chunkId) return false;
        return true;
      });
      if (!selected) {
        selected = citations.find(
          (entry) => entry && typeof entry.citation_id === "string" && entry.citation_id.trim() === citationId
        );
      }
    }
    if (!selected && documentId) {
      selected = citations.find((entry) => {
        const target = resolveCitationTarget(entry);
        if (!target || target.documentId !== documentId) return false;
        if (pageNumber && target.pageNumber !== pageNumber) return false;
        if (chunkId && textValue(target.chunkId) !== chunkId) return false;
        return true;
      });
    }
    if (!selected) return;
    previewState.lastDeepLinkKey = deepLinkKey;
    openCitationPreview(selected, null, citations);
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
    preview.highlightColor = "";
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
        const unavailablePage = Number(docMeta.requested_page) || Number(docMeta.page_number) || pageNumber;
        const unavailablePageCount = Number(docMeta.page_count) || unavailablePage;
        preview.pageCount = unavailablePageCount;
        preview.pageNumber = unavailablePage;
        preview.pageLabel.textContent = unavailablePageCount > 0 ? `Page ${unavailablePage} of ${unavailablePageCount}` : "";
        const name = docMeta.source_name || preview.title.textContent || "Document";
        preview.meta.textContent = `${name} - Preview unavailable`;
        preview.error.textContent = reason;
        preview.prevButton.disabled = true;
        preview.nextButton.disabled = true;
        const unavailablePdfUrl =
          typeof payload.pdf_url === "string" && payload.pdf_url
            ? payload.pdf_url
            : `/api/documents/${encodeURIComponent(documentId)}/pdf#page=${unavailablePage}`;
        preview.frame.src = buildCitationPdfPreviewUrl({
          baseUrl: unavailablePdfUrl,
          documentId: documentId,
          pageNumber: unavailablePage,
          snippet: preview.entrySnippet || fallback,
        });
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
      const pageText = typeof page.text === "string" ? page.text : "";
      const highlightsSource = Array.isArray(previewPayload.highlights) ? previewPayload.highlights : payload.highlights;
      const highlights = Array.isArray(highlightsSource) ? highlightsSource : [];
      const pdfSearchSnippet = resolvePdfSearchSnippet(preview.entrySnippet, pageText, highlights);
      preview.frame.src = buildCitationPdfPreviewUrl({
        baseUrl:
          previewPayload.pdf_url || payload.pdf_url || `/api/documents/${encodeURIComponent(documentId)}/pdf#page=${preview.pageNumber}`,
        documentId: documentId,
        pageNumber: preview.pageNumber,
        snippet: pdfSearchSnippet,
      });
      const fallbackColorIndex =
        typeof root.citationColorIndex === "function" ? root.citationColorIndex(preview.citationId || "", 8) : 0;
      renderPageText(preview.pageText, pageText, highlights, fallbackColorIndex, preview.highlightColor);
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

  function resolvePdfSearchSnippet(entrySnippet, pageText, highlights) {
    const page = typeof pageText === "string" ? pageText : "";
    const exactText = extractExactHighlightText(page, highlights);
    if (exactText) return exactText;
    if (typeof entrySnippet === "string" && entrySnippet.trim()) return entrySnippet.trim();
    return page;
  }

  function extractExactHighlightText(pageText, highlights) {
    const text = typeof pageText === "string" ? pageText : "";
    if (!text) return "";
    const items = Array.isArray(highlights) ? highlights : [];
    for (const item of items) {
      if (!item || item.status !== "exact") continue;
      const start = Number(item.start_char);
      const end = Number(item.end_char);
      if (!Number.isFinite(start) || !Number.isFinite(end)) continue;
      const startValue = Math.max(0, Math.trunc(start));
      const endValue = Math.min(text.length, Math.trunc(end));
      if (endValue <= startValue) continue;
      const chunk = text.slice(startValue, endValue).trim();
      if (chunk) return chunk;
    }
    return "";
  }

  function renderPageText(container, pageText, highlights, fallbackColorIndex, fallbackHighlightColor) {
    if (!container) return;
    const text = typeof pageText === "string" ? pageText : "";
    container.textContent = "";
    if (!text) {
      container.textContent = "No extracted text for this page.";
      return;
    }
    const ranges = normalizeHighlightRanges(highlights, text.length, fallbackColorIndex, fallbackHighlightColor);
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
      if (range.highlightColor) {
        mark.classList.add("ui-citation-highlight-custom");
        mark.style.backgroundColor = range.highlightColor;
      }
      mark.textContent = text.slice(range.start, range.end);
      fragment.appendChild(mark);
      cursor = range.end;
    });
    if (cursor < text.length) {
      fragment.appendChild(document.createTextNode(text.slice(cursor)));
    }
    container.appendChild(fragment);
  }

  function normalizeHighlightRanges(highlights, length, fallbackColorIndex, fallbackHighlightColor) {
    const items = Array.isArray(highlights) ? highlights : [];
    const ranges = [];
    const fallbackColor = Number.isFinite(fallbackColorIndex) ? Math.trunc(fallbackColorIndex) % 8 : 0;
    const fallbackColorValue = sanitizeHighlightColor(fallbackHighlightColor);
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
      const highlightColor =
        sanitizeHighlightColor(item.highlight_color) ||
        sanitizeHighlightColor(item.color) ||
        sanitizeHighlightColor(item.color_hex) ||
        fallbackColorValue;
      ranges.push({ start: startValue, end: endValue, colorIndex: colorIndex, highlightColor: highlightColor });
    });
    ranges.sort((a, b) => {
      const colorCompare = String(a.highlightColor || "").localeCompare(String(b.highlightColor || ""));
      return (a.start - b.start) || (a.end - b.end) || (a.colorIndex - b.colorIndex) || colorCompare;
    });
    const merged = [];
    ranges.forEach((range) => {
      const last = merged[merged.length - 1];
      const sameColor = String(last && last.highlightColor ? last.highlightColor : "") === String(range.highlightColor || "");
      if (!last || range.start > last.end || range.colorIndex !== last.colorIndex || !sameColor) {
        merged.push({
          start: range.start,
          end: range.end,
          colorIndex: range.colorIndex,
          highlightColor: range.highlightColor || "",
        });
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
      const entryIndex = Number.isFinite(Number(entry.index)) ? Math.max(1, Math.trunc(Number(entry.index))) : 1;
      heading.textContent = `${entryIndex}. ${entry.title || "Source"}`;
      item.appendChild(heading);
      const target = resolveCitationTarget(entry);
      if (target && target.pageNumber) {
        const meta = document.createElement("div");
        meta.className = "ui-chat-citation-meta";
        meta.textContent = `Page ${target.pageNumber}`;
        item.appendChild(meta);
      }
      const displayUrl = citationDisplayUrl(entry.url);
      if (displayUrl) {
        const link = document.createElement("a");
        link.href = displayUrl;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = displayUrl;
        item.appendChild(link);
      } else if (citationDisplaySource(entry.source_id)) {
        const sourceId = document.createElement("div");
        sourceId.className = "ui-chat-citation-source";
        sourceId.textContent = citationDisplaySource(entry.source_id);
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
      const title = sanitizeCitationTitle(entry.title, idx + 1);
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
      const safeUrl = citationDisplayUrl(entry.url);
      if (safeUrl) payload.url = safeUrl;
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
      const highlightColor = resolveCitationHighlightColor(entry);
      if (highlightColor) payload.highlight_color = highlightColor;
      normalized.push(payload);
    });
    return normalized;
  }

  function sanitizeCitationTitle(value, fallbackIndex) {
    const text = textValue(value);
    if (!text) return `Source ${fallbackIndex}`;
    if (looksLikeInternalCitationPath(text)) return `Source ${fallbackIndex}`;
    return text;
  }

  function citationDisplaySource(value) {
    const text = textValue(value);
    if (!text) return "";
    if (looksLikeInternalCitationPath(text)) return "";
    return text;
  }

  function citationDisplayUrl(value) {
    const text = textValue(value);
    if (!text) return "";
    if (looksLikeInternalCitationPath(text)) return "";
    try {
      const url = new URL(text, window.location.origin);
      const protocol = String(url.protocol || "").toLowerCase();
      if (protocol !== "http:" && protocol !== "https:") return "";
      return url.toString();
    } catch (_error) {
      return "";
    }
  }

  function looksLikeInternalCitationPath(value) {
    const text = textValue(value).toLowerCase();
    if (!text) return false;
    if (text.indexOf("/tests/") >= 0 || text.indexOf("\\tests\\") >= 0) return true;
    if (text.indexOf("__pycache__") >= 0) return true;
    if (/\.(py|pyi|ipynb)([#?].*)?$/.test(text)) return true;
    return false;
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
