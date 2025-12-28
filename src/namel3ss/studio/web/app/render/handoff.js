(() => {
  const root = window.N3App || (window.N3App = {});
  const render = root.render || (root.render = {});
  const utils = root.utils;
  const state = root.state;
  let handlersReady = false;

  function renderHandoff(data) {
    const nextValue = data || state.getCachedHandoffs();
    state.setCachedHandoffs(nextValue);
    setupHandoffHandlers();
    const panel = document.getElementById("handoffPanel");
    if (!panel) return;
    if (!data || data.ok === false) {
      const error = (data && data.error) || "Unable to load handoff data";
      renderAgents([]);
      renderPackets([], error);
      return;
    }
    renderAgents(data.agents || []);
    renderPackets(data.packets || [], null);
  }

  function renderAgents(agents) {
    const container = document.getElementById("handoffAgents");
    if (!container) return;
    container.innerHTML = "";
    if (!agents || !agents.length) {
      utils.showEmpty(container, "No agents are defined.");
      return;
    }
    const list = document.createElement("div");
    list.className = "list";
    agents.forEach((agent) => {
      const item = document.createElement("div");
      item.className = "list-item";
      const title = document.createElement("div");
      title.className = "list-title";
      title.textContent = agent.name || agent.agent_id || "Agent";
      const meta = document.createElement("div");
      meta.className = "list-meta";
      meta.textContent = agent.ai_name ? `ai: ${agent.ai_name}` : "ai: unknown";
      item.appendChild(title);
      item.appendChild(meta);
      list.appendChild(item);
    });
    container.appendChild(list);
    populateAgentSelects(agents);
  }

  function populateAgentSelects(agents) {
    const fromSelect = document.getElementById("handoffFrom");
    const toSelect = document.getElementById("handoffTo");
    if (!fromSelect || !toSelect) return;
    const selectedFrom = fromSelect.value;
    const selectedTo = toSelect.value;
    fromSelect.innerHTML = "";
    toSelect.innerHTML = "";
    agents.forEach((agent) => {
      const option = document.createElement("option");
      option.value = agent.agent_id || agent.name;
      option.textContent = agent.name || agent.agent_id;
      fromSelect.appendChild(option.cloneNode(true));
      toSelect.appendChild(option);
    });
    if (selectedFrom) fromSelect.value = selectedFrom;
    if (selectedTo) toSelect.value = selectedTo;
  }

  function renderPackets(packets, errorText) {
    const container = document.getElementById("handoffPackets");
    if (!container) return;
    container.innerHTML = "";
    if (!packets || !packets.length) {
      utils.showEmpty(container, errorText || "No handoff packets.");
      return;
    }
    const list = document.createElement("div");
    list.className = "list";
    packets.forEach((packet) => {
      const item = document.createElement("div");
      item.className = "list-item handoff-item";
      const title = document.createElement("div");
      title.className = "list-title";
      title.textContent = packet.packet_id || "Handoff packet";
      const meta = document.createElement("div");
      meta.className = "list-meta";
      meta.textContent = packetMeta(packet);
      item.appendChild(title);
      item.appendChild(meta);
      const summary = buildSummaryBlock(packet.summary_lines || []);
      item.appendChild(summary);
      const preview = buildPreviewBlock(packet.previews || []);
      item.appendChild(preview);
      if (packet.status === "pending") {
        const actions = document.createElement("div");
        actions.className = "list-actions";
        const applyBtn = document.createElement("button");
        applyBtn.className = "btn ghost small";
        applyBtn.textContent = "Apply";
        applyBtn.onclick = () => applyHandoff(packet.packet_id);
        const rejectBtn = document.createElement("button");
        rejectBtn.className = "btn ghost small";
        rejectBtn.textContent = "Reject";
        rejectBtn.onclick = () => rejectHandoff(packet.packet_id);
        actions.appendChild(applyBtn);
        actions.appendChild(rejectBtn);
        item.appendChild(actions);
      }
      list.appendChild(item);
    });
    container.appendChild(list);
  }

  function packetMeta(packet) {
    const parts = [];
    if (packet.status) parts.push(`status: ${packet.status}`);
    if (packet.from_agent_id) parts.push(`from: ${packet.from_agent_id}`);
    if (packet.to_agent_id) parts.push(`to: ${packet.to_agent_id}`);
    if (packet.item_count !== undefined) parts.push(`items: ${packet.item_count}`);
    if (packet.phase_id) parts.push(`phase: ${packet.phase_id}`);
    if (packet.created_by) parts.push(`by: ${packet.created_by}`);
    return parts.join(" | ");
  }

  function buildSummaryBlock(lines) {
    const block = document.createElement("div");
    block.className = "handoff-summary";
    if (!lines || !lines.length) {
      block.textContent = "No briefing lines.";
      return block;
    }
    block.appendChild(utils.createCodeBlock(lines.join("\n")));
    return block;
  }

  function buildPreviewBlock(previews) {
    const block = document.createElement("div");
    block.className = "handoff-preview";
    if (!previews || !previews.length) {
      block.textContent = "No packet items.";
      return block;
    }
    const lines = previews.map((entry) => formatPreview(entry));
    block.appendChild(utils.createCodeBlock(lines.join("\n")));
    return block;
  }

  function formatPreview(entry) {
    const parts = [];
    if (entry.memory_id) parts.push(`id: ${entry.memory_id}`);
    if (entry.event_type) parts.push(`type: ${entry.event_type}`);
    if (entry.preview) parts.push(`preview: ${entry.preview}`);
    return parts.join(" | ");
  }

  async function refreshHandoff() {
    const data = await utils.fetchJson("/api/memory/handoff");
    renderHandoff(data);
  }

  async function createHandoff() {
    const fromSelect = document.getElementById("handoffFrom");
    const toSelect = document.getElementById("handoffTo");
    const fromAgent = fromSelect ? fromSelect.value : "";
    const toAgent = toSelect ? toSelect.value : "";
    if (!fromAgent || !toAgent) {
      utils.showToast("Both agents are required.");
      return;
    }
    const res = await fetch("/api/memory/handoff/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from_agent_id: fromAgent, to_agent_id: toAgent }),
    });
    const data = await res.json();
    if (!data.ok) {
      utils.showToast("Handoff creation failed.");
      if (data.error) utils.showToast(data.error);
      return;
    }
    if (Array.isArray(data.traces) && data.traces.length) {
      state.setCachedTraces(state.getCachedTraces().concat(data.traces));
      if (window.renderTraces) window.renderTraces(state.getCachedTraces());
    }
    renderHandoff(data);
  }

  async function applyHandoff(packetId) {
    if (!packetId) return;
    const res = await fetch("/api/memory/handoff/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ packet_id: packetId }),
    });
    const data = await res.json();
    if (!data.ok) {
      utils.showToast("Handoff apply failed.");
      if (data.error) utils.showToast(data.error);
      return;
    }
    if (Array.isArray(data.traces) && data.traces.length) {
      state.setCachedTraces(state.getCachedTraces().concat(data.traces));
      if (window.renderTraces) window.renderTraces(state.getCachedTraces());
    }
    renderHandoff(data);
  }

  async function rejectHandoff(packetId) {
    if (!packetId) return;
    const res = await fetch("/api/memory/handoff/reject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ packet_id: packetId }),
    });
    const data = await res.json();
    if (!data.ok) {
      utils.showToast("Handoff reject failed.");
      if (data.error) utils.showToast(data.error);
      return;
    }
    if (Array.isArray(data.traces) && data.traces.length) {
      state.setCachedTraces(state.getCachedTraces().concat(data.traces));
      if (window.renderTraces) window.renderTraces(state.getCachedTraces());
    }
    renderHandoff(data);
  }

  function setupHandoffHandlers() {
    if (handlersReady) return;
    handlersReady = true;
    const refreshBtn = document.getElementById("handoffRefresh");
    if (refreshBtn) refreshBtn.onclick = refreshHandoff;
    const createBtn = document.getElementById("handoffCreate");
    if (createBtn) createBtn.onclick = createHandoff;
  }

  render.renderHandoff = renderHandoff;
  render.refreshHandoff = refreshHandoff;
  window.renderHandoff = renderHandoff;
  window.refreshHandoff = refreshHandoff;
})();
