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
