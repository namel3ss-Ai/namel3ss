(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom;
  const net = root.net;
  const why = root.why || (root.why = {});

  let cachedPayload = null;
  let loading = false;

  function formatCapsules(capsules) {
    if (!Array.isArray(capsules) || !capsules.length) return "none";
    return capsules
      .slice(0, 3)
      .map((item) => `${item.name || "capsule"} source ${item.source || "unknown"}`)
      .join(", ");
  }

  function formatRequires(rules) {
    if (!Array.isArray(rules) || !rules.length) return "no explicit rules";
    return rules
      .slice(0, 3)
      .map((rule) => `${rule.scope || "?"} ${rule.name || "?"} requires ${rule.rule || "?"}`)
      .join("; ");
  }

  function formatPersistence(persistence) {
    if (!persistence || typeof persistence !== "object") return "memory";
    const target = persistence.target || "memory";
    const descriptor = persistence.descriptor;
    return descriptor ? `${target} ${descriptor}` : String(target);
  }

  function buildWhyLines(payload) {
    const pages = payload.pages || 0;
    const flows = payload.flows || 0;
    const records = payload.records || 0;
    const engine = payload.engine_target || "unknown";
    const proof = payload.proof_id || "none";
    const verify = payload.verify_status || "unknown";
    return [
      `Execution environment: ${engine}.`,
      `App shape: ${pages} pages, ${flows} flows, ${records} records.`,
      `Capsules: ${formatCapsules(payload.capsules || [])}.`,
      `Access rules: ${formatRequires(payload.requires || [])}.`,
      `Persistence: ${formatPersistence(payload.persistence)}.`,
      `Run summary: ${proof}.`,
      `Verify: ${verify}.`,
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

    buildWhyLines(payload).forEach((line) => {
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
