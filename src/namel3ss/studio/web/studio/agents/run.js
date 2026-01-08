(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const dom = root.dom;
  const net = root.net;
  const actionResult = root.actionResult || {};
  const agents = root.agents || (root.agents = {});
  const runner = agents.run || (agents.run = {});

  let payloadRows = [{ key: "", value: "" }];

  function buildRunSection(payload) {
    const section = document.createElement("div");
    section.className = "agent-section";
    const header = document.createElement("div");
    header.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Run Agents";
    header.appendChild(title);
    section.appendChild(header);

    const agentsList = Array.isArray(payload.agents) ? payload.agents : [];
    if (!agentsList.length) {
      section.appendChild(dom.buildEmpty("No agents declared in this app."));
      return section;
    }

    const list = document.createElement("div");
    list.className = "list";
    agentsList.forEach((agent) => {
      const row = document.createElement("div");
      row.className = "agent-row";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.dataset.agentName = agent.name;
      const label = document.createElement("div");
      label.className = "agent-row-label";
      label.textContent = agent.name;
      const meta = document.createElement("div");
      meta.className = "agent-row-meta";
      meta.textContent = agent.ai_name ? `AI: ${agent.ai_name}` : "";
      row.appendChild(checkbox);
      row.appendChild(label);
      row.appendChild(meta);
      list.appendChild(row);
    });

    const inputWrap = document.createElement("div");
    inputWrap.className = "agent-form";
    const messageRow = document.createElement("div");
    messageRow.className = "agent-grid-row";
    const messageLabel = document.createElement("label");
    messageLabel.textContent = "Message";
    const messageInput = document.createElement("input");
    messageInput.type = "text";
    messageInput.placeholder = "Ask for a summary or a plan...";
    messageRow.appendChild(messageLabel);
    messageRow.appendChild(messageInput);
    inputWrap.appendChild(messageRow);

    const payloadBlock = document.createElement("div");
    payloadBlock.className = "agent-payload";
    const payloadTitle = document.createElement("div");
    payloadTitle.className = "panel-section-title";
    payloadTitle.textContent = "Structured payload (optional)";
    payloadBlock.appendChild(payloadTitle);
    const payloadList = document.createElement("div");
    payloadList.className = "agent-payload-list";
    payloadBlock.appendChild(payloadList);
    const addField = document.createElement("button");
    addField.type = "button";
    addField.className = "btn ghost";
    addField.textContent = "Add field";
    addField.onclick = () => {
      payloadRows.push({ key: "", value: "" });
      renderPayloadRows(payloadList);
    };
    payloadBlock.appendChild(addField);
    inputWrap.appendChild(payloadBlock);
    renderPayloadRows(payloadList);

    const actions = document.createElement("div");
    actions.className = "agent-actions";
    const runButton = document.createElement("button");
    runButton.type = "button";
    runButton.className = "btn primary";
    runButton.textContent = "Run selected";
    runButton.onclick = async () => {
      await runSelectedAgents(list, messageInput.value, false);
    };
    const parallelButton = document.createElement("button");
    parallelButton.type = "button";
    parallelButton.className = "btn ghost";
    parallelButton.textContent = "Run parallel";
    parallelButton.onclick = async () => {
      await runSelectedAgents(list, messageInput.value, true);
    };
    actions.appendChild(runButton);
    actions.appendChild(parallelButton);
    inputWrap.appendChild(actions);

    const lastRun = document.createElement("div");
    lastRun.className = "agent-last";
    renderLastRun(lastRun);
    const timeline = document.createElement("div");
    timeline.className = "agent-timeline";
    renderTimeline(timeline);

    section.appendChild(list);
    section.appendChild(inputWrap);
    section.appendChild(lastRun);
    section.appendChild(timeline);
    return section;
  }

  function renderPayloadRows(container) {
    container.innerHTML = "";
    payloadRows.forEach((row, index) => {
      const wrapper = document.createElement("div");
      wrapper.className = "agent-payload-row";
      const keyInput = document.createElement("input");
      keyInput.type = "text";
      keyInput.placeholder = "key";
      keyInput.value = row.key;
      keyInput.oninput = (event) => {
        payloadRows[index].key = event.target.value;
      };
      const valueInput = document.createElement("input");
      valueInput.type = "text";
      valueInput.placeholder = "value";
      valueInput.value = row.value;
      valueInput.oninput = (event) => {
        payloadRows[index].value = event.target.value;
      };
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "btn ghost";
      remove.textContent = "Remove";
      remove.onclick = () => {
        payloadRows = payloadRows.filter((_, idx) => idx !== index);
        if (!payloadRows.length) payloadRows = [{ key: "", value: "" }];
        renderPayloadRows(container);
      };
      wrapper.appendChild(keyInput);
      wrapper.appendChild(valueInput);
      wrapper.appendChild(remove);
      container.appendChild(wrapper);
    });
  }

  function collectPayload() {
    const data = {};
    payloadRows.forEach((row) => {
      const key = (row.key || "").trim();
      if (!key) return;
      data[key] = row.value || "";
    });
    return data;
  }

  async function runSelectedAgents(listNode, message, parallel) {
    const selected = Array.from(listNode.querySelectorAll("input[type=checkbox]")).filter((box) => box.checked);
    if (!selected.length) {
      dom.showError(document.getElementById("agents"), "Select at least one agent to run.");
      return;
    }
    const inputText = (message || "").trim();
    if (!inputText) {
      dom.showError(document.getElementById("agents"), "Provide a message to run.");
      return;
    }
    const agentNames = selected.map((box) => box.dataset.agentName).filter(Boolean);
    const payloadData = collectPayload();
    const body = { agents: agentNames, input: inputText, payload: payloadData, parallel: Boolean(parallel) };
    try {
      const result = await net.postJson("/api/agent/run", body);
      if (actionResult && typeof actionResult.applyActionResult === "function") {
        actionResult.applyActionResult(result);
      }
      if (state && typeof state.setCachedAgentRun === "function") {
        state.setCachedAgentRun(result);
      }
      renderLastRun(document.getElementById("agents").querySelector(".agent-last"));
      renderTimeline(document.getElementById("agents").querySelector(".agent-timeline"));
    } catch (err) {
      dom.showError(
        document.getElementById("agents"),
        err && err.message ? err.message : "Unable to run agent.",
      );
    }
  }

  function renderLastRun(container) {
    if (!container) return;
    container.innerHTML = "";
    const last = state && typeof state.getCachedAgentRun === "function" ? state.getCachedAgentRun() : null;
    if (!last) {
      container.appendChild(dom.buildEmpty("No agent run yet."));
      return;
    }
    const summary = document.createElement("div");
    summary.className = "agent-last-summary";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Last result";
    const output = document.createElement("div");
    output.className = "agent-last-output";
    output.textContent = typeof last.result === "string" ? last.result : JSON.stringify(last.result || "", null, 2);
    summary.appendChild(title);
    summary.appendChild(output);
    if (Array.isArray(last.traces) && last.traces.length) {
      const meta = document.createElement("div");
      meta.className = "agent-last-meta";
      const trace = last.traces[0] || {};
      meta.textContent = trace.title || "Trace captured.";
      summary.appendChild(meta);
    }
    container.appendChild(summary);
  }

  function renderTimeline(container) {
    if (!container) return;
    container.innerHTML = "";
    const last = state && typeof state.getCachedAgentRun === "function" ? state.getCachedAgentRun() : null;
    const explain = last && typeof last === "object" ? last.agent_explain : null;
    const timeline = explain && Array.isArray(explain.timeline) ? explain.timeline : [];
    const header = document.createElement("div");
    header.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Timeline";
    header.appendChild(title);
    container.appendChild(header);
    if (!timeline.length) {
      container.appendChild(dom.buildEmpty("No agent timeline yet."));
      return;
    }
    const list = document.createElement("div");
    list.className = "agent-timeline-list";
    timeline.forEach((event) => {
      const row = document.createElement("div");
      row.className = "agent-timeline-row";
      const label = document.createElement("div");
      label.className = "agent-timeline-title";
      label.textContent = event.title || event.kind || "Event";
      row.appendChild(label);
      const detail = document.createElement("div");
      detail.className = "agent-timeline-detail";
      detail.textContent = formatEventDetail(event);
      row.appendChild(detail);
      if (event.explain && Array.isArray(event.explain.lines)) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn ghost";
        btn.textContent = "Explain";
        const explainBox = document.createElement("div");
        explainBox.className = "agent-timeline-explain hidden";
        const explainTitle = document.createElement("div");
        explainTitle.className = "agent-timeline-explain-title";
        explainTitle.textContent = event.explain.title || "Explanation";
        explainBox.appendChild(explainTitle);
        event.explain.lines.forEach((line) => {
          const lineEl = document.createElement("div");
          lineEl.className = "agent-timeline-explain-line";
          lineEl.textContent = line;
          explainBox.appendChild(lineEl);
        });
        btn.onclick = () => {
          explainBox.classList.toggle("hidden");
        };
        row.appendChild(btn);
        row.appendChild(explainBox);
      }
      list.appendChild(row);
    });
    container.appendChild(list);
  }

  function formatEventDetail(event) {
    const details = event.details || {};
    if (event.kind === "memory") {
      const count = details.recalled_count ?? 0;
      const spaces = Array.isArray(details.spaces) ? details.spaces.join(", ") : "";
      return `recalled: ${count}${spaces ? ` | spaces: ${spaces}` : ""}`;
    }
    if (event.kind === "tool") {
      const status = details.status || "requested";
      const decision = details.decision ? ` | ${details.decision}` : "";
      return `${status}${decision}`;
    }
    if (event.kind === "output") {
      return details.output_preview || "";
    }
    if (event.kind === "merge") {
      return details.merge_policy || "";
    }
    if (event.kind === "handoff") {
      const from = details.from_agent_id || "";
      const to = details.to_agent_id || "";
      if (from || to) return `${from} → ${to}`.trim();
    }
    return "";
  }

  runner.buildRunSection = buildRunSection;
})();
