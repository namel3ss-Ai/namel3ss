(() => {
let cachedAuditFilter = { kind: "", text: "" };

function setupDataPanel() {
  const refreshButton = document.getElementById("dataRefresh");
  if (refreshButton) {
    refreshButton.onclick = () => refreshDataPanel();
  }
  const applyButton = document.getElementById("auditFilterApply");
  if (applyButton) {
    applyButton.onclick = () => refreshDataPanel();
  }
}

async function refreshDataPanel() {
  const summaryEl = document.getElementById("dataSummary");
  if (summaryEl) {
    summaryEl.innerHTML = "";
    showStatus(summaryEl, "Loading data summary…", "loading");
  }
  const filterKind = document.getElementById("auditFilterKind");
  const filterText = document.getElementById("auditFilterText");
  cachedAuditFilter = {
    kind: filterKind ? filterKind.value : "",
    text: filterText ? filterText.value.trim() : "",
  };
  try {
    const [summary, audit] = await Promise.all([
      fetchJson("/api/data/summary"),
      fetchJson(`/api/audit?limit=50&filter=${encodeURIComponent(buildAuditFilter(cachedAuditFilter))}`),
    ]);
    renderDataSummary(summary);
    renderAuditTimeline(audit);
  } catch (err) {
    if (summaryEl) {
      showStatus(summaryEl, "Unable to load data summary.", "error");
    }
  }
}

function renderDataSummary(payload) {
  const container = document.getElementById("dataSummary");
  if (!container) return;
  container.innerHTML = "";
  const header = buildSectionHeader("Engine + Identity");
  container.appendChild(header);
  if (!payload || payload.ok === false) {
    showStatus(container, payload && payload.error ? payload.error : "Unable to load summary.", "error");
    return;
  }
  const kv = document.createElement("div");
  kv.className = "key-values";
  kv.innerHTML = `
    <div class=\"kv-row\"><div class=\"kv-label\">engine</div><div class=\"kv-value\">${payload.engine_target || "unknown"}</div></div>
    <div class=\"kv-row\"><div class=\"kv-label\">persistence</div><div class=\"kv-value\">${formatPersistence(payload.persistence)}</div></div>
    <div class=\"kv-row\"><div class=\"kv-label\">identity</div><div class=\"kv-value\">${formatIdentity(payload.identity)}</div></div>
    <div class=\"kv-row\"><div class=\"kv-label\">tenant</div><div class=\"kv-value\">${formatTenant(payload.tenant)}</div></div>
  `;
  container.appendChild(kv);
}

function renderAuditTimeline(payload) {
  const container = document.getElementById("auditEvents");
  if (!container) return;
  container.innerHTML = "";
  if (!payload || payload.status === "error") {
    showStatus(container, payload && payload.error ? payload.error : "Unable to load audit.", "error");
    return;
  }
  const events = Array.isArray(payload.events) ? payload.events : [];
  if (!events.length) {
    showEmpty(container, "No recent audit events");
    return;
  }
  events.forEach((event) => {
    const row = document.createElement("div");
    row.className = "audit-event";
    row.textContent = formatAuditEvent(event);
    container.appendChild(row);
  });
}

function buildAuditFilter(filter) {
  if (!filter || !filter.text) return "";
  if (filter.kind === "flow") return `flow:${filter.text}`;
  if (filter.kind === "action") return `action:${filter.text}`;
  return filter.text;
}

function formatAuditEvent(event) {
  if (!event) return "audit";
  const time = event.timestamp ? new Date(event.timestamp * 1000).toISOString() : "unknown time";
  const flow = event.flow || "";
  const action = event.action || "";
  const actor = event.actor ? "actor" : "";
  const parts = [flow, action, actor].filter(Boolean).join(" · ");
  return `${time} · ${parts || "event"}`;
}

function formatPersistence(persistence) {
  if (!persistence) return "unknown";
  const target = persistence.target || "memory";
  const descriptor = persistence.descriptor;
  return descriptor ? `${target} (${descriptor})` : target;
}

function formatIdentity(identity) {
  if (!identity) return "unknown";
  const mode = identity.mode || "none";
  const defaults = Array.isArray(identity.defaults) ? identity.defaults.length : 0;
  return defaults ? `${mode} (${defaults} defaults)` : mode;
}

function formatTenant(tenant) {
  if (!tenant) return "none";
  if (!tenant.enabled) return "off";
  const keys = Array.isArray(tenant.keys) ? tenant.keys.join(", ") : "";
  return keys ? `on (${keys})` : "on";
}

function buildSectionHeader(title) {
  const header = document.createElement("div");
  header.className = "panel-section";
  const label = document.createElement("div");
  label.className = "panel-section-title";
  label.textContent = title;
  header.appendChild(label);
  return header;
}

function showStatus(container, message, kind) {
  const banner = document.createElement("div");
  banner.className = `status-banner ${kind || ""}`.trim();
  banner.textContent = message;
  container.appendChild(banner);
}

setupDataPanel();
refreshDataPanel();
window.refreshDataPanel = refreshDataPanel;
})();
