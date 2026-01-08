(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom;
  const net = root.net;
  const agents = root.agents || (root.agents = {});
  const memoryPacks = agents.memoryPacks || (agents.memoryPacks = {});

  function buildMemoryPacksSection(payload, onRefresh) {
    const section = document.createElement("div");
    section.className = "agent-section";
    const header = document.createElement("div");
    header.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Memory Packs";
    header.appendChild(title);
    section.appendChild(header);

    const packs = Array.isArray(payload.memory_packs) ? payload.memory_packs : [];
    if (!packs.length) {
      section.appendChild(dom.buildEmpty("No memory packs available."));
      return section;
    }

    const selection = payload.memory_pack_selection || {};
    const appSelection = selection.app || {};
    const agentSelection = selection.agents || {};

    const form = document.createElement("div");
    form.className = "agent-form";

    const appRow = buildSelectRow(
      "App default pack",
      buildPackOptions(packs, true),
      packValueFromSelection(appSelection, true),
      () => {}
    );
    form.appendChild(appRow);

    const agentsList = Array.isArray(payload.agents) ? payload.agents : [];
    if (agentsList.length) {
      const agentHeader = document.createElement("div");
      agentHeader.className = "agent-note";
      agentHeader.textContent = "Per-agent overrides (optional)";
      form.appendChild(agentHeader);
      agentsList.forEach((agent) => {
        const agentRow = buildSelectRow(
          agent.name,
          buildPackOptions(packs, false),
          packValueFromSelection(agentSelection[agent.name] || {}, false),
          () => {}
        );
        agentRow.dataset.agentName = agent.name;
        form.appendChild(agentRow);
      });
    }

    const actions = document.createElement("div");
    actions.className = "agent-actions";
    const applyBtn = document.createElement("button");
    applyBtn.type = "button";
    applyBtn.className = "btn primary";
    applyBtn.textContent = "Apply pack settings";
    applyBtn.onclick = async () => {
      await applyPackSettings(form, onRefresh);
    };
    actions.appendChild(applyBtn);
    form.appendChild(actions);

    const diff = document.createElement("div");
    diff.className = "agent-pack-diff";
    renderDiffLines(diff, payload.diff_lines || []);
    section.appendChild(form);
    section.appendChild(diff);
    return section;
  }

  function buildPackOptions(packs, includeAuto) {
    const options = [];
    if (includeAuto) options.push({ id: "auto", label: "Auto (project packs)" });
    options.push({ id: "none", label: "None" });
    packs.forEach((pack) => {
      const label = `${pack.name || pack.id} (${pack.source || "pack"})`;
      options.push({ id: pack.id, label });
    });
    if (!includeAuto) options.unshift({ id: "inherit", label: "Inherit app default" });
    return options;
  }

  function packValueFromSelection(selection, isApp) {
    if (!selection || typeof selection !== "object") {
      return isApp ? "auto" : "inherit";
    }
    if (!isApp && selection.source !== "agent_override") {
      return "inherit";
    }
    if (selection.mode === "none") {
      return "none";
    }
    if (selection.pack_id) {
      return selection.pack_id;
    }
    return isApp ? "auto" : "inherit";
  }

  function buildSelectRow(label, options, selectedValue, onChange) {
    const row = document.createElement("div");
    row.className = "agent-grid-row";
    const lab = document.createElement("label");
    lab.textContent = label;
    const select = document.createElement("select");
    (options || []).forEach((opt) => {
      const option = document.createElement("option");
      option.value = opt.id;
      option.textContent = opt.label || opt.id;
      select.appendChild(option);
    });
    select.value = selectedValue;
    select.onchange = (event) => onChange(event.target.value);
    row.appendChild(lab);
    row.appendChild(select);
    return row;
  }

  async function applyPackSettings(form, onRefresh) {
    const rows = Array.from(form.querySelectorAll(".agent-grid-row"));
    const payload = { default_pack: "auto", agent_overrides: {} };
    rows.forEach((row) => {
      const label = row.querySelector("label");
      const select = row.querySelector("select");
      if (!label || !select) return;
      const name = label.textContent || "";
      if (name === "App default pack") {
        payload.default_pack = select.value;
        return;
      }
      const agentName = row.dataset.agentName;
      if (agentName) {
        payload.agent_overrides[agentName] = select.value;
      }
    });
    try {
      const result = await net.postJson("/api/agent/memory_packs", payload);
      if (result && result.ok === false) {
        dom.showError(document.getElementById("agents"), result.error || "Unable to update memory packs.");
        return;
      }
      if (onRefresh) {
        await onRefresh();
      }
      if (result && result.diff_lines) {
        renderDiffLines(form.parentElement.querySelector(".agent-pack-diff"), result.diff_lines);
      }
    } catch (err) {
      dom.showError(
        document.getElementById("agents"),
        err && err.message ? err.message : "Unable to update memory packs.",
      );
    }
  }

  function renderDiffLines(container, lines) {
    if (!container) return;
    container.innerHTML = "";
    const diffLines = Array.isArray(lines) ? lines : [];
    if (!diffLines.length) {
      container.appendChild(dom.buildEmpty("No pack changes yet."));
      return;
    }
    diffLines.forEach((line) => {
      const row = document.createElement("div");
      row.className = "agent-pack-diff-line";
      row.textContent = line;
      container.appendChild(row);
    });
  }

  memoryPacks.buildMemoryPacksSection = buildMemoryPacksSection;
})();
