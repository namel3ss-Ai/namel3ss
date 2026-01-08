(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom;
  const net = root.net;
  const agents = root.agents || (root.agents = {});
  const wizard = agents.wizard || (agents.wizard = {});

  let wizardState = null;

  function ensureWizardState(payload) {
    if (wizardState) return wizardState;
    const patterns = payload && Array.isArray(payload.patterns) ? payload.patterns : [];
    const defaultPattern = patterns.length ? patterns[0].id : "router";
    wizardState = {
      pattern: defaultPattern,
      createAi: true,
      aiName: `${defaultPattern}_ai`,
      aiProvider: "mock",
      aiModel: "mock-model",
      aiMemory: "minimal",
      aiTools: new Set(),
      agents: {},
      toolName: "",
    };
    applyRoleDefaults(wizardState, payload);
    return wizardState;
  }

  function applyRoleDefaults(stateValue, payload) {
    const patterns = payload && Array.isArray(payload.patterns) ? payload.patterns : [];
    const match = patterns.find((item) => item.id === stateValue.pattern);
    if (!match) return;
    const roles = Array.isArray(match.roles) ? match.roles : [];
    roles.forEach((role) => {
      if (!stateValue.agents[role]) {
        stateValue.agents[role] = `${role}_agent`;
      }
    });
    if (!stateValue.aiName) {
      stateValue.aiName = `${stateValue.pattern}_ai`;
    }
  }

  function buildWizardSection(payload, callbacks = {}) {
    const stateValue = ensureWizardState(payload);
    const section = document.createElement("div");
    section.className = "agent-section";

    const header = document.createElement("div");
    header.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Agent Wizard";
    header.appendChild(title);
    section.appendChild(header);

    const form = document.createElement("div");
    form.className = "agent-form";

    const patterns = Array.isArray(payload.patterns) ? payload.patterns : [];
    form.appendChild(buildSelectRow("Pattern", patterns, stateValue.pattern, (value) => {
      stateValue.pattern = value;
      applyRoleDefaults(stateValue, payload);
      if (callbacks.onUpdate) callbacks.onUpdate();
    }));

    const aiProfiles = Array.isArray(payload.ais) ? payload.ais : [];
    const aiOptions = [{ id: "__new__", label: "Create new (mock)" }, ...aiProfiles.map((ai) => ({ id: ai.name, label: ai.name }))];
    const aiChoice = stateValue.createAi ? "__new__" : stateValue.aiName;
    form.appendChild(buildSelectRow("AI profile", aiOptions, aiChoice, (value) => {
      if (value === "__new__") {
        stateValue.createAi = true;
        stateValue.aiName = `${stateValue.pattern}_ai`;
      } else {
        stateValue.createAi = false;
        stateValue.aiName = value;
      }
      if (callbacks.onUpdate) callbacks.onUpdate();
    }));

    if (stateValue.createAi) {
      form.appendChild(buildInputRow("AI name", stateValue.aiName, (value) => {
        stateValue.aiName = value;
      }));
      form.appendChild(buildInputRow("Model", stateValue.aiModel, (value) => {
        stateValue.aiModel = value;
      }));
      form.appendChild(buildProviderRow(stateValue, aiProfiles));
      form.appendChild(buildMemoryRow(stateValue, payload));
      form.appendChild(buildToolRow(stateValue, payload));
    } else {
      const note = document.createElement("div");
      note.className = "agent-note";
      note.textContent = "Using existing AI profile; tool and memory settings remain unchanged.";
      form.appendChild(note);
    }

    const roles = findPatternRoles(payload, stateValue.pattern);
    const roleGrid = document.createElement("div");
    roleGrid.className = "agent-grid";
    roles.forEach((role) => {
      const row = document.createElement("div");
      row.className = "agent-grid-row";
      const label = document.createElement("label");
      label.textContent = `${role} agent`;
      const input = document.createElement("input");
      input.type = "text";
      input.value = stateValue.agents[role] || "";
      input.oninput = (event) => {
        stateValue.agents[role] = event.target.value;
      };
      row.appendChild(label);
      row.appendChild(input);
      roleGrid.appendChild(row);
    });
    form.appendChild(roleGrid);

    if (patternRequiresTools(payload, stateValue.pattern)) {
      const toolRow = document.createElement("div");
      toolRow.className = "agent-grid-row";
      const label = document.createElement("label");
      label.textContent = "Tool";
      const toolSelect = document.createElement("select");
      const tools = Array.isArray(payload.tools) ? payload.tools : [];
      tools.forEach((tool) => {
        const option = document.createElement("option");
        option.value = tool.name;
        option.textContent = tool.name;
        toolSelect.appendChild(option);
      });
      toolSelect.value = stateValue.toolName || (tools[0] && tools[0].name) || "";
      toolSelect.onchange = (event) => {
        stateValue.toolName = event.target.value;
      };
      toolRow.appendChild(label);
      toolRow.appendChild(toolSelect);
      form.appendChild(toolRow);
      if (!tools.length) {
        const warning = document.createElement("div");
        warning.className = "agent-warning";
        warning.textContent = "Tool-first requires at least one declared tool.";
        form.appendChild(warning);
      }
    }

    const actions = document.createElement("div");
    actions.className = "agent-actions";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn primary";
    button.textContent = "Generate";
    button.onclick = async () => {
      await submitWizard(payload, callbacks.onRefresh);
    };
    actions.appendChild(button);
    form.appendChild(actions);

    section.appendChild(form);
    return section;
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

  function buildInputRow(label, value, onChange) {
    const row = document.createElement("div");
    row.className = "agent-grid-row";
    const lab = document.createElement("label");
    lab.textContent = label;
    const input = document.createElement("input");
    input.type = "text";
    input.value = value || "";
    input.oninput = (event) => onChange(event.target.value);
    row.appendChild(lab);
    row.appendChild(input);
    return row;
  }

  function buildProviderRow(stateValue, aiProfiles) {
    const providers = new Set(["mock", "openai", "anthropic", "gemini", "mistral"]);
    (aiProfiles || []).forEach((ai) => {
      if (ai.provider) providers.add(ai.provider);
    });
    const options = Array.from(providers).sort().map((value) => ({ id: value, label: value }));
    return buildSelectRow("Provider", options, stateValue.aiProvider, (value) => {
      stateValue.aiProvider = value;
    });
  }

  function buildMemoryRow(stateValue, payload) {
    const presets = Array.isArray(payload.memory_presets) ? payload.memory_presets : [];
    const options = presets.map((preset) => ({ id: preset.id, label: preset.label }));
    return buildSelectRow("Memory", options, stateValue.aiMemory, (value) => {
      stateValue.aiMemory = value;
    });
  }

  function buildToolRow(stateValue, payload) {
    const tools = Array.isArray(payload.tools) ? payload.tools : [];
    const wrapper = document.createElement("div");
    wrapper.className = "agent-tool-list";
    const label = document.createElement("div");
    label.className = "agent-tool-label";
    label.textContent = "Expose tools";
    wrapper.appendChild(label);
    if (!tools.length) {
      const empty = document.createElement("div");
      empty.className = "agent-note";
      empty.textContent = "No tools declared in this app.";
      wrapper.appendChild(empty);
      return wrapper;
    }
    tools.forEach((tool) => {
      const row = document.createElement("label");
      row.className = "agent-tool-row";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = stateValue.aiTools.has(tool.name);
      checkbox.onchange = () => {
        if (checkbox.checked) {
          stateValue.aiTools.add(tool.name);
        } else {
          stateValue.aiTools.delete(tool.name);
        }
      };
      const span = document.createElement("span");
      span.textContent = tool.name;
      row.appendChild(checkbox);
      row.appendChild(span);
      wrapper.appendChild(row);
    });
    return wrapper;
  }

  function findPatternRoles(payload, patternId) {
    const patterns = Array.isArray(payload.patterns) ? payload.patterns : [];
    const match = patterns.find((item) => item.id === patternId);
    return match && Array.isArray(match.roles) ? match.roles : [];
  }

  function patternRequiresTools(payload, patternId) {
    const patterns = Array.isArray(payload.patterns) ? payload.patterns : [];
    const match = patterns.find((item) => item.id === patternId);
    return Boolean(match && match.requires_tools);
  }

  async function submitWizard(payload, onRefresh) {
    const stateValue = ensureWizardState(payload);
    const data = {
      pattern: stateValue.pattern,
      create_ai: stateValue.createAi,
      ai_name: stateValue.aiName,
      ai_provider: stateValue.aiProvider,
      ai_model: stateValue.aiModel,
      ai_memory: stateValue.aiMemory,
      ai_tools: Array.from(stateValue.aiTools),
      agents: stateValue.agents,
      tool_name: stateValue.toolName || "",
    };
    try {
      const result = await net.postJson("/api/agent/wizard", data);
      if (result && result.ok === false) {
        dom.showError(document.getElementById("agents"), result.error || "Unable to generate agent.");
        return;
      }
      if (root.refresh && root.refresh.refreshUI) {
        await root.refresh.refreshUI();
      }
      if (root.refresh && root.refresh.refreshSummary) {
        await root.refresh.refreshSummary();
      }
      if (onRefresh) {
        await onRefresh();
      }
    } catch (err) {
      dom.showError(
        document.getElementById("agents"),
        err && err.message ? err.message : "Unable to generate agent.",
      );
    }
  }

  wizard.buildWizardSection = buildWizardSection;
})();
