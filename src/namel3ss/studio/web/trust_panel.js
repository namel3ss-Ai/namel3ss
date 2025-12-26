(() => {
let cachedTrust = {
  summary: null,
  proof: null,
  verify: null,
  secrets: null,
  observe: null,
  explain: null,
  why: null,
};

function setupTrustPanel() {
  const refreshButton = document.getElementById("trustRefresh");
  if (refreshButton) {
    refreshButton.onclick = () => refreshTrustPanel();
  }
}

async function refreshTrustPanel() {
  const statusEl = document.getElementById("trustStatus");
  if (statusEl) {
    statusEl.innerHTML = "";
    showStatus(statusEl, "Loading trust summary…", "loading");
  }
  try {
    const [summary, secrets, observe, explain, why] = await Promise.all([
      fetchJson("/api/trust/summary"),
      fetchJson("/api/trust/secrets"),
      fetchJson("/api/trust/observe?limit=50"),
      fetchJson("/api/trust/explain"),
      fetchJson("/api/why"),
    ]);
    cachedTrust.summary = summary;
    cachedTrust.secrets = secrets;
    cachedTrust.observe = observe;
    cachedTrust.explain = explain;
    cachedTrust.why = why;
    renderTrustSummary(summary);
    renderTrustSecrets(secrets);
    renderTrustObserve(observe);
    renderTrustExplain(explain);
    renderTrustWhy(why);
    renderTrustProof(cachedTrust.proof);
    renderTrustVerify(cachedTrust.verify);
  } catch (err) {
    if (statusEl) {
      showStatus(statusEl, "Unable to load trust data.", "error");
    }
  }
}

function renderTrustSummary(payload) {
  const container = document.getElementById("trustStatus");
  if (!container) return;
  container.innerHTML = "";
  const header = buildSectionHeader("Engine status");
  container.appendChild(header);
  if (!payload || payload.ok === false) {
    showStatus(container, payload && payload.error ? payload.error : "Unable to load summary.", "error");
    return;
  }
  const kv = document.createElement("div");
  kv.className = "key-values";
  kv.innerHTML = `
    <div class=\"kv-row\"><div class=\"kv-label\">engine</div><div class=\"kv-value\">${payload.engine_target || "unknown"}</div></div>
    <div class=\"kv-row\"><div class=\"kv-label\">proof</div><div class=\"kv-value\">${payload.active_proof_id || "none"}</div></div>
    <div class=\"kv-row\"><div class=\"kv-label\">build</div><div class=\"kv-value\">${payload.active_build_id || payload.active_pack_id || "none"}</div></div>
    <div class=\"kv-row\"><div class=\"kv-label\">persistence</div><div class=\"kv-value\">${formatPersistence(payload.persistence)}</div></div>
  `;
  container.appendChild(kv);
}

function renderTrustProof(payload) {
  const container = document.getElementById("trustProof");
  if (!container) return;
  container.innerHTML = "";
  const header = buildSectionHeader("Proof", [
    buildButton("Open proof (JSON)", "secondary", async () => {
      try {
        const resp = await fetchJson("/api/trust/proof");
        cachedTrust.proof = resp;
        renderTrustProof(resp);
      } catch (err) {
        showToast("Proof fetch failed.");
      }
    }),
    buildButton("Copy", "ghost", () => copyText(payload || {}), true),
  ]);
  container.appendChild(header);
  if (!payload) {
    showEmpty(container, "No proof loaded yet.");
    return;
  }
  if (payload.ok === false) {
    showStatus(container, payload.error || "No active proof recorded.", "warning");
    return;
  }
  const block = createCodeBlock(payload);
  container.appendChild(block);
}

function renderTrustVerify(payload) {
  const container = document.getElementById("trustVerify");
  if (!container) return;
  container.innerHTML = "";
  const header = buildSectionHeader("Verify", [
    buildButton("Verify for prod", "primary", async () => {
      try {
        const resp = await postJson("/api/trust/verify", { prod: true });
        cachedTrust.verify = resp;
        renderTrustVerify(resp);
      } catch (err) {
        showToast("Verify failed.");
      }
    }),
    buildButton("Copy", "ghost", () => copyText(payload || {}), true),
  ]);
  container.appendChild(header);
  if (!payload) {
    showEmpty(container, "Run verify to see results.");
    return;
  }
  const status = payload.status || payload.ok;
  const badge = document.createElement("div");
  badge.className = `badge ${status === "ok" ? "ok" : "bad"}`;
  badge.textContent = status || "unknown";
  container.appendChild(badge);
  const checks = Array.isArray(payload.checks) ? payload.checks : [];
  const failures = checks.filter((check) => check.status && check.status !== "ok");
  if (!failures.length) {
    const note = document.createElement("div");
    note.className = "empty-hint";
    note.textContent = "No failing checks.";
    container.appendChild(note);
    return;
  }
  const list = document.createElement("div");
  list.className = "list";
  failures.slice(0, 3).forEach((check) => {
    const item = document.createElement("div");
    item.className = "list-item";
    item.innerHTML = `<div class=\"list-title\">${check.id}</div><div class=\"list-meta\">${check.message || ""}</div>`;
    list.appendChild(item);
  });
  container.appendChild(list);
}

function renderTrustSecrets(payload) {
  const container = document.getElementById("trustSecrets");
  if (!container) return;
  container.innerHTML = "";
  container.appendChild(buildSectionHeader("Secrets"));
  if (!payload || !Array.isArray(payload.secrets)) {
    showStatus(container, "Unable to load secrets.", "error");
    return;
  }
  if (!payload.secrets.length) {
    showEmpty(container, "No secrets required.");
    return;
  }
  const list = document.createElement("div");
  list.className = "list";
  payload.secrets.forEach((secret) => {
    const item = document.createElement("div");
    item.className = "list-item";
    item.innerHTML = `<div class=\"list-title\">${secret.name}</div><div class=\"list-meta\">${secret.available ? "available" : "missing"}</div>`;
    list.appendChild(item);
  });
  container.appendChild(list);
}

function renderTrustObserve(payload) {
  const container = document.getElementById("trustObserve");
  if (!container) return;
  container.innerHTML = "";
  container.appendChild(buildSectionHeader("Observe"));
  const events = payload && Array.isArray(payload.events) ? payload.events : [];
  if (!events.length) {
    showEmpty(container, "No recent events.");
    return;
  }
  const list = document.createElement("div");
  list.className = "panel-stack";
  events.slice(-50).reverse().forEach((event) => {
    const row = document.createElement("div");
    row.className = "audit-event";
    row.textContent = formatEvent(event);
    list.appendChild(row);
  });
  container.appendChild(list);
}

function renderTrustExplain(payload) {
  const container = document.getElementById("trustExplain");
  if (!container) return;
  container.innerHTML = "";
  container.appendChild(buildSectionHeader("Explain"));
  if (!payload || payload.ok === false) {
    showStatus(container, payload && payload.error ? payload.error : "Unable to load explain.", "error");
    return;
  }
  const summary = document.createElement("div");
  summary.className = "panel-stack";
  const governance = payload.governance || {};
  const tools = Array.isArray(payload.tools) ? payload.tools.length : 0;
  const access = payload.access_rules || {};
  const flows = Array.isArray(access.flows) ? access.flows.length : 0;
  const pages = Array.isArray(access.pages) ? access.pages.length : 0;
  summary.innerHTML = `
    <div>Engine target: ${payload.engine_target || "unknown"}</div>
    <div>Governance: ${governance.status || "unknown"}</div>
    <div>Access rules: ${flows} flows, ${pages} pages</div>
    <div>Tools reviewed: ${tools}</div>
  `;
  container.appendChild(summary);
}

function renderTrustWhy(payload) {
  const container = document.getElementById("trustWhy");
  if (!container) return;
  container.innerHTML = "";
  container.appendChild(buildSectionHeader("Why"));
  if (!payload || payload.ok === false) {
    showStatus(container, payload && payload.error ? payload.error : "Unable to load why.", "error");
    return;
  }
  const lines = [];
  lines.push(`Engine target: ${payload.engine_target || "unknown"}`);
  lines.push(`Capsules: ${formatWhyCapsules(payload.capsules || [])}`);
  lines.push(`Access rules: ${formatWhyRules(payload.requires || [])}`);
  lines.push(`Persistence: ${formatPersistence(payload.persistence)}`);
  lines.push(`Proof: ${payload.proof_id || "none"}`);
  lines.push(`Verify: ${payload.verify_status || "unknown"}`);
  const list = document.createElement("div");
  list.className = "panel-stack";
  lines.forEach((line) => {
    const item = document.createElement("div");
    item.textContent = line;
    list.appendChild(item);
  });
  container.appendChild(list);
}

function buildSectionHeader(title, actions = []) {
  const header = document.createElement("div");
  header.className = "panel-section";
  const label = document.createElement("div");
  label.className = "panel-section-title";
  label.textContent = title;
  header.appendChild(label);
  if (actions.length) {
    const actionRow = document.createElement("div");
    actionRow.className = "json-actions";
    actions.forEach((action) => actionRow.appendChild(action));
    header.appendChild(actionRow);
  }
  return header;
}

function buildButton(label, variant, handler, compact = false) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `btn ${variant}${compact ? " small" : ""}`.trim();
  button.textContent = label;
  button.onclick = handler;
  return button;
}

function formatPersistence(persistence) {
  if (!persistence) return "unknown";
  const target = persistence.target || "memory";
  const descriptor = persistence.descriptor;
  return descriptor ? `${target} (${descriptor})` : target;
}

function formatWhyCapsules(capsules) {
  if (!capsules.length) return "none";
  return capsules.map((c) => `${c.name} (${c.source})`).join(", ");
}

function formatWhyRules(rules) {
  if (!rules.length) return "no explicit rules";
  return rules.slice(0, 2).map((r) => `${r.scope} ${r.name} requires ${r.rule}`).join("; ");
}

function formatEvent(event) {
  if (!event) return "event";
  const time = event.time ? new Date(event.time * 1000).toISOString() : "unknown time";
  const label = event.type || "event";
  const flow = event.flow ? `flow:${event.flow}` : "";
  const action = event.action ? `action:${event.action}` : "";
  const parts = [label, flow, action].filter(Boolean);
  return `${time} · ${parts.join(" · ")}`;
}

function showStatus(container, message, kind) {
  const banner = document.createElement("div");
  banner.className = `status-banner ${kind || ""}`.trim();
  banner.textContent = message;
  container.appendChild(banner);
}

async function postJson(path, payload) {
  const resp = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  return resp.json();
}

setupTrustPanel();
refreshTrustPanel();
window.refreshTrustPanel = refreshTrustPanel;
})();
