(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom;
  const net = root.net;
  const why = root.why || (root.why = {});

  let cachedPayload = null;
  let loading = false;

  function formatValue(value) {
    if (value === null || value === undefined) return "None";
    return String(value);
  }

  function truncate(text, limit) {
    if (!text) return "";
    if (text.length <= limit) return text;
    return `${text.slice(0, limit - 1)}…`;
  }

  function buildExplainLines(payload) {
    const access = payload && payload.access_rules ? payload.access_rules : {};
    const flows = Array.isArray(access.flows) ? access.flows : [];
    const pages = Array.isArray(access.pages) ? access.pages : [];
    const tenant = payload && payload.tenant_scoping ? payload.tenant_scoping : {};
    const governance = payload && payload.governance ? payload.governance : {};
    const tenantCount = Object.prototype.hasOwnProperty.call(tenant, "count") ? tenant.count : 0;
    const governanceStatus = Object.prototype.hasOwnProperty.call(governance, "status") ? governance.status : "unknown";
    return [
      `Engine target: ${formatValue(payload && payload.engine_target)}`,
      `Active proof: ${formatValue(payload && payload.active_proof_id)}`,
      `Active build: ${formatValue(payload && payload.active_build_id)}`,
      `Requires rules: ${flows.length} flows, ${pages.length} pages`,
      `Tenant scoping: ${formatValue(tenantCount)} records`,
      `Governance: ${formatValue(governanceStatus)}`,
    ];
  }

  function buildRouteLine(route) {
    if (!route) return "";
    const method = route.method || "METHOD";
    const path = route.path || "/path";
    const flow = route.flow || "flow";
    const parts = [`${method} ${path} -> ${flow}`];
    const paramText = formatFieldBlock(route.parameters);
    if (paramText) parts.push(`params: ${paramText}`);
    const requestText = formatFieldBlock(route.request);
    if (requestText) parts.push(`request: ${requestText}`);
    const responseText = formatFieldBlock(route.response);
    if (responseText) parts.push(`response: ${responseText}`);
    if (route.upload) parts.push("upload");
    if (route.generated) parts.push("generated");
    return parts.join(" | ");
  }

  function formatFieldBlock(fields) {
    if (!Array.isArray(fields) || fields.length === 0) return "";
    return fields
      .map((entry) => `${entry.name} is ${entry.type}`)
      .join(", ");
  }

  function buildAiLine(entry) {
    if (!entry) return "";
    const parts = [`${entry.flow}: ${entry.model}`];
    if (entry.prompt) {
      parts.push(`prompt "${truncate(entry.prompt, 80)}"`);
    }
    if (entry.dataset) {
      parts.push(`dataset "${entry.dataset}"`);
    }
    if (entry.output_type) {
      parts.push(`output ${entry.output_type}`);
    }
    if (Array.isArray(entry.labels) && entry.labels.length) {
      parts.push(`labels: ${entry.labels.join(", ")}`);
    }
    if (Array.isArray(entry.sources) && entry.sources.length) {
      parts.push(`sources: ${entry.sources.join(", ")}`);
    }
    return parts.join(" | ");
  }

  function buildCrudLine(entry) {
    if (!entry) return "";
    return `crud ${entry.record || "record"}`;
  }

  function buildPromptLine(entry) {
    if (!entry) return "";
    const name = entry.name || "prompt";
    const version = entry.version ? `v${entry.version}` : "version";
    const parts = [`${name} ${version}`];
    if (entry.description) {
      parts.push(`about "${truncate(entry.description, 80)}"`);
    }
    if (entry.text) {
      parts.push(`text "${truncate(entry.text, 80)}"`);
    }
    return parts.join(" | ");
  }

  function buildAiFlowLine(entry) {
    if (!entry) return "";
    const kind = entry.kind || "ai_flow";
    const name = entry.name || "flow";
    const parts = [`${kind} ${name}`];
    if (entry.model) parts.push(`model ${entry.model}`);
    if (entry.prompt) parts.push(`prompt "${truncate(entry.prompt, 80)}"`);
    if (entry.dataset) parts.push(`dataset "${entry.dataset}"`);
    if (entry.output_type) parts.push(`output ${entry.output_type}`);
    if (Array.isArray(entry.labels) && entry.labels.length) {
      parts.push(`labels: ${entry.labels.join(", ")}`);
    }
    if (Array.isArray(entry.sources) && entry.sources.length) {
      parts.push(`sources: ${entry.sources.join(", ")}`);
    }
    return parts.join(" | ");
  }

  function buildDatasetLine(entry) {
    if (!entry) return "";
    const name = entry.name || entry.dataset_id || "dataset";
    const source = entry.source ? `source ${entry.source}` : "";
    const parts = [name];
    if (source) parts.push(source);
    if (entry.owner) parts.push(`owner ${entry.owner}`);
    return parts.join(" | ");
  }

  function renderWhy(payload) {
    const panel = document.getElementById("why");
    if (!panel) return;
    panel.innerHTML = "";
    if (!payload || payload.ok === false) {
      const message = payload && payload.error ? payload.error : "Unable to load why summary.";
      dom.showError(panel, message);
      return;
    }
    const wrapper = document.createElement("div");
    wrapper.className = "why-panel";
    const title = document.createElement("div");
    title.className = "why-title";
    title.textContent = "Why this app is safe to run.";
    wrapper.appendChild(title);

    const section = document.createElement("div");
    section.className = "why-section";
    const heading = document.createElement("div");
    heading.className = "why-section-title";
    heading.textContent = "Summary";
    const list = document.createElement("ul");
    list.className = "why-list";

    buildExplainLines(payload).forEach((line) => {
      const li = document.createElement("li");
      li.textContent = line;
      list.appendChild(li);
    });

    section.appendChild(heading);
    section.appendChild(list);
    wrapper.appendChild(section);

    const routes = Array.isArray(payload.routes) ? payload.routes : [];
    if (routes.length) {
      const routeSection = document.createElement("div");
      routeSection.className = "why-section";
      const routeHeading = document.createElement("div");
      routeHeading.className = "why-section-title";
      routeHeading.textContent = "Routes";
      const routeList = document.createElement("ul");
      routeList.className = "why-list";
      routes.forEach((route) => {
        const li = document.createElement("li");
        li.textContent = buildRouteLine(route);
        routeList.appendChild(li);
      });
      routeSection.appendChild(routeHeading);
      routeSection.appendChild(routeList);
      wrapper.appendChild(routeSection);
    }

    const crud = Array.isArray(payload.crud) ? payload.crud : [];
    if (crud.length) {
      const crudSection = document.createElement("div");
      crudSection.className = "why-section";
      const crudHeading = document.createElement("div");
      crudHeading.className = "why-section-title";
      crudHeading.textContent = "CRUD";
      const crudList = document.createElement("ul");
      crudList.className = "why-list";
      crud.forEach((entry) => {
        const li = document.createElement("li");
        li.textContent = buildCrudLine(entry);
        crudList.appendChild(li);
      });
      crudSection.appendChild(crudHeading);
      crudSection.appendChild(crudList);
      wrapper.appendChild(crudSection);
    }

    const prompts = Array.isArray(payload.prompts) ? payload.prompts : [];
    if (prompts.length) {
      const promptSection = document.createElement("div");
      promptSection.className = "why-section";
      const promptHeading = document.createElement("div");
      promptHeading.className = "why-section-title";
      promptHeading.textContent = "Prompts";
      const promptList = document.createElement("ul");
      promptList.className = "why-list";
      prompts.forEach((entry) => {
        const li = document.createElement("li");
        li.textContent = buildPromptLine(entry);
        promptList.appendChild(li);
      });
      promptSection.appendChild(promptHeading);
      promptSection.appendChild(promptList);
      wrapper.appendChild(promptSection);
    }

    const aiFlows = Array.isArray(payload.ai_flows) ? payload.ai_flows : [];
    if (aiFlows.length) {
      const aiFlowSection = document.createElement("div");
      aiFlowSection.className = "why-section";
      const aiFlowHeading = document.createElement("div");
      aiFlowHeading.className = "why-section-title";
      aiFlowHeading.textContent = "AI Flows";
      const aiFlowList = document.createElement("ul");
      aiFlowList.className = "why-list";
      aiFlows.forEach((entry) => {
        const li = document.createElement("li");
        li.textContent = buildAiFlowLine(entry);
        aiFlowList.appendChild(li);
      });
      aiFlowSection.appendChild(aiFlowHeading);
      aiFlowSection.appendChild(aiFlowList);
      wrapper.appendChild(aiFlowSection);
    }

    const aiMetadata = Array.isArray(payload.ai_metadata) ? payload.ai_metadata : [];
    if (aiMetadata.length) {
      const aiSection = document.createElement("div");
      aiSection.className = "why-section";
      const aiHeading = document.createElement("div");
      aiHeading.className = "why-section-title";
      aiHeading.textContent = "AI Metadata";
      const aiList = document.createElement("ul");
      aiList.className = "why-list";
      aiMetadata.forEach((entry) => {
        const li = document.createElement("li");
        li.textContent = buildAiLine(entry);
        aiList.appendChild(li);
      });
      aiSection.appendChild(aiHeading);
      aiSection.appendChild(aiList);
      wrapper.appendChild(aiSection);
    }

    const datasets = Array.isArray(payload.datasets) ? payload.datasets : [];
    if (datasets.length) {
      const datasetSection = document.createElement("div");
      datasetSection.className = "why-section";
      const datasetHeading = document.createElement("div");
      datasetHeading.className = "why-section-title";
      datasetHeading.textContent = "Datasets";
      const datasetList = document.createElement("ul");
      datasetList.className = "why-list";
      datasets.forEach((entry) => {
        const li = document.createElement("li");
        li.textContent = buildDatasetLine(entry);
        datasetList.appendChild(li);
      });
      datasetSection.appendChild(datasetHeading);
      datasetSection.appendChild(datasetList);
      wrapper.appendChild(datasetSection);
    }
    panel.appendChild(wrapper);
  }

  async function refreshWhyPanel() {
    const panel = document.getElementById("why");
    if (!panel) return;
    if (cachedPayload) {
      renderWhy(cachedPayload);
      return;
    }
    if (loading) return;
    loading = true;
    dom.showEmpty(panel, "Loading why summary...");
    try {
      const payload = await net.fetchJson("/api/why");
      cachedPayload = payload;
      renderWhy(payload);
    } catch (err) {
      const detail = err && err.message ? err.message : "Unable to load why summary.";
      dom.showError(panel, detail);
    } finally {
      loading = false;
    }
  }

  why.renderWhy = renderWhy;
  why.refreshWhyPanel = refreshWhyPanel;
  window.renderWhy = renderWhy;
  window.refreshWhyPanel = refreshWhyPanel;
})();
