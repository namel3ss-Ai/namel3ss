(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});

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
    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = "Type a message";
    const button = document.createElement("button");
    button.type = "submit";
    button.className = "btn small";
    button.textContent = "Send";
    form.appendChild(input);
    form.appendChild(button);

    form.onsubmit = async (e) => {
      e.preventDefault();
      const message = input.value || "";
      input.value = "";
      await handleAction(
        { id: child.action_id, type: "call_flow", flow: child.flow },
        { message },
        button
      );
    };
    return form;
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
