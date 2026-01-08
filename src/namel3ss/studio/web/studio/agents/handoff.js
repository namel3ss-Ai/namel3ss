(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom;
  const net = root.net;
  const actionResult = root.actionResult || {};
  const agents = root.agents || (root.agents = {});
  const handoff = agents.handoff || (agents.handoff = {});

  function buildHandoffSection(payload, onRefresh) {
    const section = document.createElement("div");
    section.className = "agent-section";
    const header = document.createElement("div");
    header.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Handoff";
    header.appendChild(title);
    section.appendChild(header);

    const agentsList = Array.isArray(payload.agents) ? payload.agents : [];
    if (agentsList.length < 2) {
      section.appendChild(dom.buildEmpty("Handoff requires at least two agents."));
      return section;
    }

    const form = document.createElement("div");
    form.className = "handoff-form";
    const fromRow = document.createElement("div");
    fromRow.className = "agent-grid-row";
    const fromLabel = document.createElement("label");
    fromLabel.textContent = "From agent";
    const fromSelect = buildAgentSelect(agentsList);
    fromRow.appendChild(fromLabel);
    fromRow.appendChild(fromSelect);
    const toRow = document.createElement("div");
    toRow.className = "agent-grid-row";
    const toLabel = document.createElement("label");
    toLabel.textContent = "To agent";
    const toSelect = buildAgentSelect(agentsList);
    toRow.appendChild(toLabel);
    toRow.appendChild(toSelect);
    form.appendChild(fromRow);
    form.appendChild(toRow);

    const createBtn = document.createElement("button");
    createBtn.type = "button";
    createBtn.className = "btn ghost";
    createBtn.textContent = "Create handoff";
    createBtn.onclick = async () => {
      await runHandoffAction("create", {
        from_agent_id: fromSelect.value,
        to_agent_id: toSelect.value,
      }, onRefresh);
    };
    form.appendChild(createBtn);
    section.appendChild(form);

    const handoffs = Array.isArray(payload.handoffs) ? payload.handoffs : [];
    if (!handoffs.length) {
      section.appendChild(dom.buildEmpty("No pending handoffs."));
      return section;
    }

    const list = document.createElement("div");
    list.className = "handoff-list";
    handoffs.forEach((handoffItem) => {
      const item = document.createElement("div");
      item.className = "handoff-item";
      const summary = document.createElement("div");
      summary.className = "handoff-summary";
      const itemTitle = document.createElement("div");
      itemTitle.className = "handoff-title";
      itemTitle.textContent = `Packet ${handoffItem.packet_id}`;
      const meta = document.createElement("div");
      meta.className = "handoff-meta";
      meta.textContent = `${handoffItem.from_agent_id} → ${handoffItem.to_agent_id}`;
      summary.appendChild(itemTitle);
      summary.appendChild(meta);
      item.appendChild(summary);
      const lines = document.createElement("div");
      lines.className = "handoff-preview";
      const summaryLines = Array.isArray(handoffItem.summary_lines) ? handoffItem.summary_lines : [];
      summaryLines.forEach((line) => {
        const row = document.createElement("div");
        row.className = "handoff-line";
        row.textContent = line;
        lines.appendChild(row);
      });
      const previews = Array.isArray(handoffItem.previews) ? handoffItem.previews : [];
      const groups = groupPreviews(previews);
      groups.forEach((group) => {
        const header = document.createElement("div");
        header.className = "handoff-group-title";
        header.textContent = group.label;
        lines.appendChild(header);
        group.items.forEach((preview) => {
          const row = document.createElement("div");
          row.className = "handoff-line";
          row.textContent = `${preview.kind}: ${preview.preview}`;
          lines.appendChild(row);
          if (preview.why) {
            const reason = document.createElement("div");
            reason.className = "handoff-line handoff-why";
            reason.textContent = preview.why;
            lines.appendChild(reason);
          }
        });
      });
      item.appendChild(lines);
      const applyBtn = document.createElement("button");
      applyBtn.type = "button";
      applyBtn.className = "btn primary";
      applyBtn.textContent = "Apply";
      applyBtn.onclick = async () => {
        await runHandoffAction("apply", { packet_id: handoffItem.packet_id }, onRefresh);
      };
      item.appendChild(applyBtn);
      list.appendChild(item);
    });
    section.appendChild(list);
    return section;
  }

  function buildAgentSelect(agentsList) {
    const select = document.createElement("select");
    agentsList.forEach((agent) => {
      const option = document.createElement("option");
      option.value = agent.name;
      option.textContent = agent.name;
      select.appendChild(option);
    });
    return select;
  }

  function groupPreviews(previews) {
    const order = ["decisions", "proposals", "conflicts", "rules", "impact", "other", "missing"];
    const labels = {
      decisions: "Decisions",
      proposals: "Proposals",
      conflicts: "Conflicts",
      rules: "Rules",
      impact: "Impact warnings",
      other: "Other",
      missing: "Missing items",
    };
    const grouped = new Map();
    previews.forEach((preview) => {
      const key = preview.category || "other";
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key).push(preview);
    });
    const result = [];
    order.forEach((key) => {
      const items = grouped.get(key);
      if (!items || !items.length) return;
      result.push({ key, label: labels[key] || key, items });
    });
    return result;
  }

  async function runHandoffAction(action, extra, onRefresh) {
    try {
      const result = await net.postJson("/api/agent/handoff", { action, ...extra });
      if (actionResult && typeof actionResult.applyActionResult === "function") {
        actionResult.applyActionResult(result);
      }
      if (onRefresh) {
        await onRefresh();
      }
    } catch (err) {
      dom.showError(
        document.getElementById("agents"),
        err && err.message ? err.message : "Unable to run handoff.",
      );
    }
  }

  handoff.buildHandoffSection = buildHandoffSection;
})();
