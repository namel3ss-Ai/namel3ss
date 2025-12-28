let cachedSummary = {};
let cachedState = {};
let cachedActions = {};
let cachedTraces = [];
let cachedAgreements = {};
let cachedLint = {};
let cachedTools = {};
let cachedPacks = {};
let cachedSecurity = {};
let cachedManifest = null;
let traceFilterText = "";
let traceFilterTimer = null;
let traceRenderMode = "plain";
let tracePhaseMode = "current";
let traceLaneMode = "my";
let toolsFilterText = "";
let toolsFilterTimer = null;
let selectedTrace = null;
let selectedElementId = null;
let selectedElement = null;
let selectedPage = null;
let versionLabel = null;
let themeSetting = "system";
let runtimeTheme = null;
let themeOverride = null;
let seedActionId = null;
let preferencePolicy = { allow_override: false, persist: "none" };
function copyText(value) {
  if (!value && value !== "") return;
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).catch(() => {});
  } else {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
  }
}
function getPersistenceInfo() {
  const persistence = (cachedManifest && cachedManifest.ui && cachedManifest.ui.persistence) || {};
  const kind = (persistence.kind || "memory").toLowerCase();
  return {
    enabled: !!persistence.enabled,
    kind,
    path: persistence.path || "",
  };
}
function updateCopyButton(id, getter) {
  const btn = document.getElementById(id);
  if (!btn) return;
  btn.onclick = () => copyText(getter());
}
function fetchJson(path, options) {
  return fetch(path, options).then((res) => res.json());
}
function showEmpty(container, message) {
  container.innerHTML = "";
  const empty = document.createElement("div");
  empty.className = "empty-state";
  empty.textContent = message;
  container.appendChild(empty);
}
function showToast(message) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.style.display = "block";
  setTimeout(() => {
    toast.style.display = "none";
  }, 2000);
}
function createCodeBlock(content) {
  const pre = document.createElement("pre");
  pre.className = "code-block";
  pre.textContent = typeof content === "string" ? content : JSON.stringify(content, null, 2);
  return pre;
}
function setFileName(path) {
  const label = document.getElementById("fileName");
  if (!label) return;
  if (!path) {
    label.textContent = "";
    return;
  }
  const parts = path.split(/[\\/]/);
  label.textContent = parts[parts.length - 1];
}
function setVersionLabel(version) {
  versionLabel = versionLabel || document.getElementById("versionLabel");
  if (versionLabel) versionLabel.textContent = version ? `namel3ss v${version}` : "";
}
function renderSummary(data) {
  cachedSummary = data || {};
  const container = document.getElementById("summary"); if (!container) return; container.innerHTML = "";
  if (!data || data.ok === false) {
    showEmpty(container, data && data.error ? data.error : "Unable to load summary");
    updateCopyButton("summaryCopy", () => "");
    return;
  }
  setFileName(data.file);
  const counts = data.counts || {};
  const kv = document.createElement("div");
  kv.className = "key-values";
  Object.keys(counts).forEach((key) => {
    const row = document.createElement("div");
    row.className = "kv-row";
    row.innerHTML = `<div class="kv-label">${key}</div><div class="kv-value">${counts[key]}</div>`;
    kv.appendChild(row);
  });
  if (cachedManifest && cachedManifest.theme) {
    const setting = cachedManifest.theme.setting || "system";
    const runtime = cachedManifest.theme.current || setting;
    const display = themeOverride || runtime;
    const effective = resolveTheme(display);
    const tokenMap = applyThemeTokens(cachedManifest.theme.tokens || {}, display);
    const row = document.createElement("div");
    row.className = "kv-row";
    const overrideLabel = themeOverride ? " (preview override)" : "";
    row.innerHTML = `<div class="kv-label">theme</div><div class="kv-value">setting: ${setting}, engine: ${runtime}, effective: ${effective}${overrideLabel}</div>`;
    kv.appendChild(row);
    const tokensRow = document.createElement("div");
    tokensRow.className = "kv-row";
    tokensRow.innerHTML = `<div class="kv-label">tokens</div><div class="kv-value">${JSON.stringify(tokenMap)}</div>`;
    kv.appendChild(tokensRow);
    const pref = cachedManifest.theme.preference || {};
    const prefRow = document.createElement("div");
    prefRow.className = "kv-row";
    prefRow.innerHTML = `<div class="kv-label">preference</div><div class="kv-value">allow_override: ${pref.allow_override ? "true" : "false"}, persist: ${pref.persist || "none"}</div>`;
    kv.appendChild(prefRow);
  }
  container.appendChild(kv);
  updateCopyButton("summaryCopy", () => JSON.stringify(data, null, 2));
}
function renderActions(data) {
  cachedActions = data || {};
  const container = document.getElementById("actions"); if (!container) return; container.innerHTML = "";
  if (!data || data.ok === false) {
    showEmpty(container, data && data.error ? data.error : "Unable to load actions");
    updateCopyButton("actionsCopy", () => "");
    return;
  }
  const actions = data.actions || [];
  if (!actions.length) {
    showEmpty(container, "No actions available.");
  } else {
    const list = document.createElement("div");
    list.className = "list";
    actions.forEach((action) => {
      const metaParts = [`type: ${action.type}`];
      if (action.flow) metaParts.push(`flow: ${action.flow}`);
      if (action.record) metaParts.push(`record: ${action.record}`);
      const item = document.createElement("div");
      item.className = "list-item";
      item.innerHTML = `<div class="list-title">${action.id}</div><div class="list-meta">${metaParts.join(" · ")}</div>`;
      list.appendChild(item);
    });
    container.appendChild(list);
  }
  updateCopyButton("actionsCopy", () => JSON.stringify(data, null, 2));
}
function renderLint(data) {
  cachedLint = data || {};
  const container = document.getElementById("lint"); if (!container) return; container.innerHTML = "";
  if (!data) {
    showEmpty(container, "Unable to load lint findings");
    updateCopyButton("lintCopy", () => "");
    return;
  }
  const findings = data.findings || [];
  if (findings.length === 0) {
    const ok = document.createElement("div");
    ok.className = "empty-state";
    ok.textContent = "OK";
    container.appendChild(ok);
  } else {
    const list = document.createElement("div");
    list.className = "list";
    findings.forEach((f) => {
      const item = document.createElement("div");
      item.className = "list-item";
      item.innerHTML = `<div class="list-title">${f.severity} ${f.code}</div><div class="list-meta">${f.message} (${f.line}:${f.column})</div>`;
      list.appendChild(item);
    });
    container.appendChild(list);
  }
  updateCopyButton("lintCopy", () => JSON.stringify(data, null, 2));
}
function renderTools(data) {
  cachedTools = data || {};
  const container = document.getElementById("tools"); if (!container) return; container.innerHTML = "";
  const fixPanel = document.getElementById("toolsFixPanel");
  if (!data || data.ok === false) {
    showEmpty(container, data && data.error ? data.error : "Unable to load tools");
    updateCopyButton("toolsCopy", () => "");
    if (fixPanel) fixPanel.classList.add("hidden");
    return;
  }
  renderToolFixes(data, fixPanel);
  const summary = data.summary || {};
  const summaryLine = document.createElement("div");
  summaryLine.className = "list-meta";
  summaryLine.textContent =
    `Summary: ok=${summary.ok || 0}, missing=${summary.missing || 0}, ` +
    `unused=${summary.unused || 0}, collisions=${summary.collisions || 0}, invalid=${summary.invalid || 0}.`;
  container.appendChild(summaryLine);

  if (data.bindings_valid === false && data.bindings_error) {
    const errorBox = document.createElement("div");
    errorBox.className = "empty-state";
    errorBox.textContent = data.bindings_error;
    container.appendChild(errorBox);
  }

  const filter = toolsFilterText.trim().toLowerCase();
  const filterItems = (items) => {
    if (!filter) return items || [];
    return (items || []).filter((item) => (item.name || "").toLowerCase().includes(filter));
  };

  renderToolSection(container, "Pack tools", filterItems(data.packs));
  renderToolSection(container, "Declared tools", filterItems(data.declared));
  renderToolSection(container, "Bound tools", filterItems(data.bindings));

  updateCopyButton("toolsCopy", () => JSON.stringify(data, null, 2));
}
function renderPacks(data) {
  cachedPacks = data || {};
  const container = document.getElementById("packs"); if (!container) return; container.innerHTML = "";
  if (!data || data.ok === false) {
    showEmpty(container, data && data.error ? data.error : "Unable to load packs");
    updateCopyButton("packsCopy", () => "");
    return;
  }
  const packs = data.packs || [];
  if (!packs.length) {
    showEmpty(container, "No packs installed.");
    updateCopyButton("packsCopy", () => JSON.stringify(data, null, 2));
    return;
  }
  const list = document.createElement("div");
  list.className = "list";
  packs.sort((a, b) => (a.pack_id || "").localeCompare(b.pack_id || "")).forEach((pack) => {
    const item = document.createElement("div");
    item.className = "list-item";
    const title = document.createElement("div");
    title.className = "list-title";
    title.textContent = `${pack.pack_id || "pack"} (${pack.version || "?"})`;
    const meta = document.createElement("div");
    meta.className = "list-meta";
    const status = pack.enabled ? "enabled" : "disabled";
    const verify = pack.verified ? "verified" : "unverified";
    meta.textContent = `${status} · ${verify} · ${pack.source || "installed"}`;
    item.appendChild(title);
    item.appendChild(meta);
    const actions = document.createElement("div");
    actions.className = "control-actions";
    if (!pack.verified) {
      const btn = document.createElement("button");
      btn.className = "btn ghost small";
      btn.textContent = "Verify";
      btn.onclick = () => packAction("/api/packs/verify", pack.pack_id);
      actions.appendChild(btn);
    }
    if (pack.verified && !pack.enabled) {
      const btn = document.createElement("button");
      btn.className = "btn ghost small";
      btn.textContent = "Enable";
      btn.onclick = () => packAction("/api/packs/enable", pack.pack_id);
      actions.appendChild(btn);
    }
    if (pack.enabled) {
      const btn = document.createElement("button");
      btn.className = "btn ghost small";
      btn.textContent = "Disable";
      btn.onclick = () => packAction("/api/packs/disable", pack.pack_id);
      actions.appendChild(btn);
    }
    item.appendChild(actions);
    list.appendChild(item);
  });
  container.appendChild(list);
  updateCopyButton("packsCopy", () => JSON.stringify(data, null, 2));
}
function renderSecurity(data) {
  cachedSecurity = data || {};
  const container = document.getElementById("security"); if (!container) return; container.innerHTML = "";
  if (!data || data.ok === false) {
    showEmpty(container, data && data.error ? data.error : "Unable to load security lens");
    updateCopyButton("securityCopy", () => "");
    return;
  }
  const tools = data.tools || [];
  if (!tools.length) {
    showEmpty(container, "No tools declared.");
    updateCopyButton("securityCopy", () => JSON.stringify(data, null, 2));
    return;
  }
  const list = document.createElement("div");
  list.className = "list";
  tools.sort((a, b) => (a.tool_name || "").localeCompare(b.tool_name || "")).forEach((tool) => {
    const item = document.createElement("div");
    item.className = "list-item";
    const title = document.createElement("div");
    title.className = "list-title";
    title.textContent = tool.tool_name || "tool";
    const meta = document.createElement("div");
    meta.className = "list-meta";
    const source = tool.resolved_source || "unknown";
    const runner = tool.runner || "unknown";
    const coverage = tool.coverage || {};
    const coverageStatus = coverage.status || "unknown";
    const sandboxEnabled = !!(tool.sandbox && tool.sandbox.enabled);
    const metaParts = [`source: ${source}`, `runner: ${runner}`, `coverage: ${coverageStatus}`];
    if (runner === "local") {
      metaParts.push(`sandbox: ${sandboxEnabled ? "on" : "off"}`);
    }
    if (runner === "service" && coverage.service_handshake) {
      metaParts.push(`handshake: ${coverage.service_handshake}`);
    }
    if (runner === "container") {
      metaParts.push(`enforcement: ${coverage.container_enforcement || "missing"}`);
    }
    meta.textContent = metaParts.join(" · ");
    const badges = document.createElement("div");
    badges.className = "badge-row";
    if (tool.blocked) {
      badges.appendChild(_badge("blocked", "bad"));
    } else {
      badges.appendChild(_badge("enforced", "ok"));
    }
    if (coverageStatus && coverageStatus !== "enforced") {
      badges.appendChild(_badge(`coverage ${coverageStatus}`, "warn"));
    }
    if (tool.unsafe_override) {
      badges.appendChild(_badge("unsafe override", "bad"));
    }
    item.appendChild(title);
    item.appendChild(meta);
    if (badges.childNodes.length) {
      item.appendChild(badges);
    }
    const guaranteesLine = document.createElement("div");
    guaranteesLine.className = "list-meta";
    guaranteesLine.textContent = `guarantees: ${_formatGuarantees(tool.guarantees || {})}`;
    item.appendChild(guaranteesLine);
    const sourcesLine = document.createElement("div");
    sourcesLine.className = "list-meta";
    sourcesLine.textContent = `sources: ${JSON.stringify(tool.guarantee_sources || {})}`;
    item.appendChild(sourcesLine);
    if (runner === "local" && tool.resolved_source === "binding") {
      const sandboxLine = document.createElement("div");
      sandboxLine.className = "list-meta";
      sandboxLine.textContent = `sandbox: ${sandboxEnabled ? "enabled" : "disabled"}`;
      item.appendChild(sandboxLine);
      const sandboxActions = document.createElement("div");
      sandboxActions.className = "control-actions";
      const sandboxBtn = document.createElement("button");
      sandboxBtn.className = "btn ghost small";
      sandboxBtn.textContent = sandboxEnabled ? "Disable sandbox" : "Enable sandbox";
      sandboxBtn.onclick = () => updateSandbox(tool.tool_name, !sandboxEnabled);
      sandboxActions.appendChild(sandboxBtn);
      item.appendChild(sandboxActions);
    }
    if (tool.blocked_reason) {
      const blocked = document.createElement("div");
      blocked.className = "list-meta";
      blocked.textContent = `blocked: ${tool.blocked_reason}`;
      item.appendChild(blocked);
    }
    item.appendChild(_renderOverrides(tool.tool_name, tool.overrides || {}));
    list.appendChild(item);
  });
  container.appendChild(list);
  updateCopyButton("securityCopy", () => JSON.stringify(data, null, 2));
}
function _badge(label, kind) {
  const badge = document.createElement("span");
  badge.className = `badge ${kind || ""}`.trim();
  badge.textContent = label;
  return badge;
}
function _formatGuarantees(guarantees) {
  const fields = [
    "no_filesystem_write",
    "no_filesystem_read",
    "no_network",
    "no_subprocess",
    "no_env_read",
    "no_env_write",
  ];
  const parts = fields.map((field) => `${field}=${guarantees[field] ? "true" : "false"}`);
  if (Array.isArray(guarantees.secrets_allowed)) {
    parts.push(`secrets_allowed=[${guarantees.secrets_allowed.join(", ")}]`);
  }
  return parts.join(" · ");
}
function _renderOverrides(toolName, overrides) {
  const wrapper = document.createElement("div");
  wrapper.className = "security-overrides";
  const heading = document.createElement("div");
  heading.className = "inline-label";
  heading.textContent = "Overrides (downgrade + unsafe)";
  wrapper.appendChild(heading);

  const grid = document.createElement("div");
  grid.className = "security-override-grid";
  const fields = [
    "no_filesystem_write",
    "no_filesystem_read",
    "no_network",
    "no_subprocess",
    "no_env_read",
    "no_env_write",
  ];
  const inputs = {};
  fields.forEach((field) => {
    const label = document.createElement("label");
    label.className = "security-override-field";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = overrides && overrides[field] === true;
    inputs[field] = input;
    label.appendChild(input);
    const span = document.createElement("span");
    span.textContent = field;
    label.appendChild(span);
    grid.appendChild(label);
  });
  wrapper.appendChild(grid);

  const secretsRow = document.createElement("label");
  secretsRow.className = "security-override-field wide";
  secretsRow.textContent = "secrets_allowed (comma separated)";
  const secretsInput = document.createElement("input");
  secretsInput.type = "text";
  secretsInput.value = Array.isArray(overrides.secrets_allowed) ? overrides.secrets_allowed.join(", ") : "";
  secretsRow.appendChild(secretsInput);
  wrapper.appendChild(secretsRow);

  const unsafeRow = document.createElement("label");
  unsafeRow.className = "security-override-field wide warning";
  const unsafeInput = document.createElement("input");
  unsafeInput.type = "checkbox";
  unsafeInput.checked = overrides && overrides.allow_unsafe_execution === true;
  unsafeRow.appendChild(unsafeInput);
  const unsafeLabel = document.createElement("span");
  unsafeLabel.textContent = "allow_unsafe_execution (bypass enforcement checks)";
  unsafeRow.appendChild(unsafeLabel);
  wrapper.appendChild(unsafeRow);

  const actions = document.createElement("div");
  actions.className = "control-actions";
  const applyBtn = document.createElement("button");
  applyBtn.className = "btn secondary small";
  applyBtn.textContent = "Apply overrides";
  applyBtn.onclick = async () => {
    if (!toolName) return;
    const warning = unsafeInput.checked ? "\nThis enables unsafe execution." : "";
    const ok = window.confirm(`Apply capability overrides for \"${toolName}\"?${warning}`);
    if (!ok) return;
    const nextOverrides = {};
    fields.forEach((field) => {
      if (inputs[field] && inputs[field].checked) {
        nextOverrides[field] = true;
      }
    });
    const secrets = secretsInput.value
      .split(",")
      .map((value) => value.trim())
      .filter((value) => value);
    if (secrets.length) {
      nextOverrides.secrets_allowed = secrets;
    }
    if (unsafeInput.checked) {
      nextOverrides.allow_unsafe_execution = true;
    }
    const okResp = await applySecurityOverride(toolName, nextOverrides);
    if (okResp) {
      refreshSecurity();
    }
  };
  actions.appendChild(applyBtn);
  wrapper.appendChild(actions);
  return wrapper;
}
async function applySecurityOverride(toolName, overrides) {
  try {
    const resp = await fetch("/api/security/override", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tool_name: toolName, overrides: overrides || {} }),
    });
    const data = await resp.json();
    if (!data.ok) {
      showToast(data.error || "Override update failed.");
      return false;
    }
    showToast("Overrides updated.");
    return true;
  } catch (err) {
    showToast("Override update failed.");
    return false;
  }
}
async function updateSandbox(toolName, enabled) {
  try {
    const resp = await fetch("/api/security/sandbox", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tool_name: toolName, enabled: !!enabled }),
    });
    const data = await resp.json();
    if (!data.ok) {
      showToast(data.error || "Sandbox update failed.");
      return;
    }
    showToast(`Sandbox ${enabled ? "enabled" : "disabled"}.`);
    refreshSecurity();
  } catch (err) {
    showToast("Sandbox update failed.");
  }
}
async function refreshSecurity() {
  try {
    const data = await fetchJson("/api/security");
    renderSecurity(data);
  } catch (err) {
    renderSecurity({ ok: false, error: "Unable to load security lens" });
  }
}
async function packAction(path, packId) {
  try {
    const resp = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pack_id: packId }),
    });
    const data = await resp.json();
    if (!data.ok) {
      showToast(data.error || "Pack action failed.");
      return;
    }
    showToast("Pack updated.");
    refreshAll();
  } catch (err) {
    showToast("Pack action failed.");
  }
}
function renderToolFixes(data, panel) {
  if (!panel) return;
  panel.innerHTML = "";
  const issues = data.issues || [];
  if (!issues.length) {
    panel.classList.add("hidden");
    return;
  }
  panel.classList.remove("hidden");
  const heading = document.createElement("div");
  heading.className = "inline-label";
  heading.textContent = "Fix suggestions";
  panel.appendChild(heading);
  const list = document.createElement("div");
  list.className = "list";
  issues.forEach((issue) => {
    const item = document.createElement("div");
    item.className = "list-item";
    const title = document.createElement("div");
    title.className = "list-title";
    const toolLabel = issue.tool_name ? ` (${issue.tool_name})` : "";
    title.textContent = `${issue.severity} ${issue.code}${toolLabel}`;
    const meta = document.createElement("div");
    meta.className = "list-meta";
    meta.textContent = issue.message || "See details.";
    item.appendChild(title);
    item.appendChild(meta);
    list.appendChild(item);
  });
  panel.appendChild(list);
}
function renderToolSection(container, title, items) {
  const heading = document.createElement("div");
  heading.className = "inline-label";
  heading.textContent = title;
  container.appendChild(heading);
  if (!items || items.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "No tools found.";
    container.appendChild(empty);
    return;
  }
  const list = document.createElement("div");
  list.className = "list";
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "list-item";
    const titleEl = document.createElement("div");
    titleEl.className = "list-title";
    titleEl.textContent = `${item.name} [${item.status}]`;
    const meta = document.createElement("div");
    meta.className = "list-meta";
    const parts = [];
    if (item.pack_id) parts.push(`pack: ${item.pack_id}`);
    if (item.source) parts.push(item.source);
    if (item.verified === false) parts.push("unverified");
    if (item.enabled === false) parts.push("disabled");
    if (item.entry) parts.push(`entry: ${item.entry}`);
    if (item.runner) parts.push(`runner: ${item.runner}`);
    if (item.kind) parts.push(`kind: ${item.kind}`);
    meta.textContent = parts.join(" · ");
    row.appendChild(titleEl);
    if (parts.length) row.appendChild(meta);
    list.appendChild(row);
  });
  container.appendChild(list);
}
function renderState(data) {
  cachedState = data || {};
  const container = document.getElementById("state"); if (!container) return; container.innerHTML = "";
  const isEmpty = !data || (Object.keys(data || {}).length === 0 && data.constructor === Object);
  if (isEmpty) {
    showEmpty(container, "State will appear here after you run an action.");
  } else {
    container.appendChild(createCodeBlock(data));
  }
  updateCopyButton("stateCopy", () => JSON.stringify(data || {}, null, 2));
}
function appendTraceSection(details, label, value, copyable = false, renderMode = "json") {
  if (value === undefined || value === null || (typeof value === "object" && Object.keys(value).length === 0)) {
    return;
  }
  const wrapper = document.createElement("div");
  const heading = document.createElement("div");
  heading.className = "inline-label";
  heading.textContent = label;
  if (copyable) {
    const copyBtn = document.createElement("button");
    copyBtn.className = "btn ghost small";
    copyBtn.textContent = "Copy";
    copyBtn.onclick = () => copyText(value);
    heading.appendChild(copyBtn);
  }
  wrapper.appendChild(heading);
  const content = renderMode === "plain" ? renderPlainTraceValue(value) : value;
  wrapper.appendChild(createCodeBlock(content));
  details.appendChild(wrapper);
}
const MEMORY_EVENT_TYPES = new Set([
  "memory_recall",
  "memory_write",
  "memory_denied",
  "memory_forget",
  "memory_conflict",
  "memory_border_check",
  "memory_promoted",
  "memory_promotion_denied",
  "memory_phase_started",
  "memory_deleted",
  "memory_phase_diff",
  "memory_links",
  "memory_path",
  "memory_impact",
  "memory_change_preview",
  "memory_team_summary",
  "memory_proposed",
  "memory_approved",
  "memory_rejected",
  "memory_agreement_summary",
  "memory_trust_check",
  "memory_approval_recorded",
  "memory_trust_rules",
]);
function appendMemoryEventsSection(details, trace, phaseId, renderMode = "json") {
  const events = buildMemoryEventEntries(trace);
  if (!events.length) return;
  const explainMap = buildMemoryExplanationMap(trace);
  const linksMap = buildMemoryLinksMap(trace);
  const pathMap = buildMemoryPathMap(trace);
  const impactMap = buildMemoryImpactMap(trace);
  const wrapper = document.createElement("div");
  const heading = document.createElement("div");
  heading.className = "inline-label";
  heading.textContent = "Memory events";
  wrapper.appendChild(heading);
  const teamSummary = traceLaneMode === "team" ? latestTeamSummary(trace) : null;
  if (teamSummary) {
    const diffEvent = findPhaseDiffEvent(trace, teamSummary);
    appendTeamSummaryBlock(wrapper, teamSummary, diffEvent, renderMode);
  }
  events.forEach((entry) => {
    const filtered = filterMemoryEventForPhase(entry.event, phaseId, tracePhaseMode);
    if (!filtered) return;
    const laneFiltered = filterMemoryEventForLane(filtered, traceLaneMode);
    if (!laneFiltered) return;
    if (teamSummary && laneFiltered.type === "memory_team_summary") return;
    const block = document.createElement("div");
    block.className = "trace-event";
    const label = document.createElement("div");
    label.className = "trace-event-label";
    label.textContent = laneFiltered.type || "memory_event";
    const memoryIds = memoryIdsForEvent(laneFiltered);
    const linkEvents = collectEventsForIds(linksMap, memoryIds);
    const pathEvents = collectEventsForIds(pathMap, memoryIds);
    const impactEventsByDepth = collectImpactEventsByDepth(impactMap, memoryIds);
    const isLinkEvent = laneFiltered.type === "memory_links" || laneFiltered.type === "memory_path";
    const isImpactEvent = laneFiltered.type === "memory_impact" || laneFiltered.type === "memory_change_preview";
    const explain = explainMap.get(entry.index);
    const contentBlock = createCodeBlock(renderMode === "plain" ? renderPlainTraceValue(laneFiltered) : laneFiltered);
    if (explain) {
      const explainBtn = document.createElement("button");
      explainBtn.className = "btn ghost small";
      explainBtn.textContent = "Explain";
      label.appendChild(explainBtn);
      const explainText = formatExplanationText(explain);
      const explainBlock = createCodeBlock(explainText);
      explainBlock.classList.add("trace-explain");
      explainBlock.style.display = "none";
      explainBtn.onclick = () => {
        const nextState = explainBlock.style.display === "none" ? "block" : "none";
        explainBlock.style.display = nextState;
      };
      block.appendChild(label);
      block.appendChild(contentBlock);
      block.appendChild(explainBlock);
      if (!isLinkEvent && linkEvents.length) {
        const linksBtn = document.createElement("button");
        linksBtn.className = "btn ghost small";
        linksBtn.textContent = "Links";
        label.appendChild(linksBtn);
        const linksText = formatLinksText(linkEvents);
        const linksBlock = createCodeBlock(linksText);
        linksBlock.classList.add("trace-links");
        linksBlock.style.display = "none";
        linksBtn.onclick = () => {
          const nextState = linksBlock.style.display === "none" ? "block" : "none";
          linksBlock.style.display = nextState;
        };
        block.appendChild(linksBlock);
      }
      if (!isLinkEvent && pathEvents.length) {
        const pathBtn = document.createElement("button");
        pathBtn.className = "btn ghost small";
        pathBtn.textContent = "Path";
        label.appendChild(pathBtn);
        const pathText = formatPathText(pathEvents);
        const pathBlock = createCodeBlock(pathText);
        pathBlock.classList.add("trace-links");
        pathBlock.style.display = "none";
        pathBtn.onclick = () => {
          const nextState = pathBlock.style.display === "none" ? "block" : "none";
          pathBlock.style.display = nextState;
        };
        block.appendChild(pathBlock);
      }
      if (!isLinkEvent && !isImpactEvent) {
        appendImpactControls(block, label, impactEventsByDepth);
      }
      wrapper.appendChild(block);
      return;
    }
    block.appendChild(label);
    block.appendChild(contentBlock);
    if (!isLinkEvent && linkEvents.length) {
      const linksBtn = document.createElement("button");
      linksBtn.className = "btn ghost small";
      linksBtn.textContent = "Links";
      label.appendChild(linksBtn);
      const linksText = formatLinksText(linkEvents);
      const linksBlock = createCodeBlock(linksText);
      linksBlock.classList.add("trace-links");
      linksBlock.style.display = "none";
      linksBtn.onclick = () => {
        const nextState = linksBlock.style.display === "none" ? "block" : "none";
        linksBlock.style.display = nextState;
      };
      block.appendChild(linksBlock);
    }
    if (!isLinkEvent && pathEvents.length) {
      const pathBtn = document.createElement("button");
      pathBtn.className = "btn ghost small";
      pathBtn.textContent = "Path";
      label.appendChild(pathBtn);
      const pathText = formatPathText(pathEvents);
      const pathBlock = createCodeBlock(pathText);
      pathBlock.classList.add("trace-links");
      pathBlock.style.display = "none";
      pathBtn.onclick = () => {
        const nextState = pathBlock.style.display === "none" ? "block" : "none";
        pathBlock.style.display = nextState;
      };
      block.appendChild(pathBlock);
    }
    if (!isLinkEvent && !isImpactEvent) {
      appendImpactControls(block, label, impactEventsByDepth);
    }
    wrapper.appendChild(block);
  });
  details.appendChild(wrapper);
}
function buildMemoryEventEntries(trace) {
  const entries = [];
  const events = trace.canonical_events || [];
  events.forEach((event, index) => {
    if (event && MEMORY_EVENT_TYPES.has(event.type)) {
      entries.push({ event, index });
    }
  });
  return entries;
}
function buildMemoryExplanationMap(trace) {
  const map = new Map();
  const events = trace.canonical_events || [];
  events.forEach((event) => {
    if (event && event.type === "memory_explanation") {
      const index = event.for_event_index;
      if (typeof index === "number") {
        map.set(index, event);
      }
    }
  });
  return map;
}
function buildMemoryLinksMap(trace) {
  const map = new Map();
  const events = trace.canonical_events || [];
  events.forEach((event) => {
    if (event && event.type === "memory_links") {
      const memoryId = event.memory_id;
      if (typeof memoryId === "string") {
        map.set(memoryId, event);
      }
    }
  });
  return map;
}
function buildMemoryPathMap(trace) {
  const map = new Map();
  const events = trace.canonical_events || [];
  events.forEach((event) => {
    if (event && event.type === "memory_path") {
      const memoryId = event.memory_id;
      if (typeof memoryId === "string") {
        map.set(memoryId, event);
      }
    }
  });
  return map;
}
function buildMemoryImpactMap(trace) {
  const map = new Map();
  const events = trace.canonical_events || [];
  events.forEach((event) => {
    if (event && event.type === "memory_impact") {
      const memoryId = event.memory_id;
      const depth = event.depth_used;
      if (typeof memoryId === "string" && typeof depth === "number") {
        const entry = map.get(memoryId) || {};
        entry[String(depth)] = event;
        map.set(memoryId, entry);
      }
    }
  });
  return map;
}
function buildTeamSummaryEntries(trace) {
  const events = trace.canonical_events || [];
  return events.filter((event) => event && event.type === "memory_team_summary");
}
function latestTeamSummary(trace) {
  const entries = buildTeamSummaryEntries(trace);
  if (!entries.length) return null;
  return entries[entries.length - 1];
}
function findPhaseDiffEvent(trace, summary) {
  if (!summary) return null;
  const events = trace.canonical_events || [];
  const summaryLane = summary.lane || "team";
  return events.find((event) => {
    if (!event || event.type !== "memory_phase_diff") return false;
    if (event.space !== summary.space) return false;
    if (event.from_phase_id !== summary.phase_from) return false;
    if (event.to_phase_id !== summary.phase_to) return false;
    if (event.lane && event.lane !== summaryLane) return false;
    return true;
  });
}
function formatTeamSummaryText(summary) {
  const lines = [];
  if (summary.title) lines.push(summary.title);
  const detail = Array.isArray(summary.lines) ? summary.lines : [];
  detail.forEach((line) => {
    if (line) lines.push(line);
  });
  return lines.join("\n");
}
function appendTeamSummaryBlock(wrapper, summary, diffEvent, renderMode) {
  const block = document.createElement("div");
  block.className = "trace-event trace-team-summary";
  const label = document.createElement("div");
  label.className = "trace-event-label";
  label.textContent = "Team summary";
  const summaryBlock = createCodeBlock(formatTeamSummaryText(summary));
  block.appendChild(label);
  block.appendChild(summaryBlock);
  if (diffEvent) {
    const diffBtn = document.createElement("button");
    diffBtn.className = "btn ghost small";
    diffBtn.textContent = "Show diff";
    label.appendChild(diffBtn);
    const diffBlock = createCodeBlock(renderMode === "plain" ? renderPlainTraceValue(diffEvent) : diffEvent);
    diffBlock.classList.add("trace-links");
    diffBlock.style.display = "none";
    diffBtn.onclick = () => {
      const nextState = diffBlock.style.display === "none" ? "block" : "none";
      diffBlock.style.display = nextState;
    };
    block.appendChild(diffBlock);
  }
  wrapper.appendChild(block);
}
function latestAgreementSummary(traces) {
  const events = [];
  (traces || []).forEach((trace) => {
    const entries = trace && trace.canonical_events ? trace.canonical_events : [];
    entries.forEach((event) => {
      if (event && event.type === "memory_agreement_summary") {
        events.push(event);
      }
    });
  });
  if (!events.length) return null;
  return events[events.length - 1];
}
function formatAgreementSummaryText(summary) {
  const lines = [];
  if (summary.title) lines.push(summary.title);
  const detail = Array.isArray(summary.lines) ? summary.lines : [];
  detail.forEach((line) => {
    if (line) lines.push(line);
  });
  return lines.join("\n");
}
function latestTrustCheck(traces) {
  const events = [];
  (traces || []).forEach((trace) => {
    const entries = trace && trace.canonical_events ? trace.canonical_events : [];
    entries.forEach((event) => {
      if (event && event.type === "memory_trust_check" && event.allowed === false) {
        events.push(event);
      }
    });
  });
  if (!events.length) return null;
  return events[events.length - 1];
}
function formatTrustLines(trust) {
  const lines = [];
  if (!trust) return "";
  const detail = Array.isArray(trust.lines) ? trust.lines : [];
  detail.forEach((line) => {
    if (line) lines.push(line);
  });
  return lines.join("\n");
}
function formatTrustNotice(traces) {
  const event = latestTrustCheck(traces);
  if (!event) return "";
  const lines = [];
  if (event.title) lines.push(event.title);
  const detail = Array.isArray(event.lines) ? event.lines : [];
  detail.forEach((line) => {
    if (line) lines.push(line);
  });
  return lines.join("\n");
}
function renderAgreements(data) {
  cachedAgreements = data || cachedAgreements;
  const panel = document.getElementById("teamAgreements");
  const list = document.getElementById("teamAgreementsList");
  const summaryBlock = document.getElementById("teamAgreementSummary");
  const trustLines = document.getElementById("teamTrustLines");
  const trustNotice = document.getElementById("teamTrustNotice");
  if (!panel || !list) return;
  if (traceLaneMode !== "team") {
    panel.classList.add("hidden");
    return;
  }
  panel.classList.remove("hidden");
  list.innerHTML = "";
  if (summaryBlock) {
    const summary = latestAgreementSummary(cachedTraces);
    summaryBlock.textContent = summary ? formatAgreementSummaryText(summary) : "No agreement summary yet.";
  }
  if (trustLines) {
    trustLines.textContent = formatTrustLines(data && data.trust ? data.trust : cachedAgreements.trust);
  }
  if (trustNotice) {
    trustNotice.textContent = formatTrustNotice(cachedTraces);
  }
  if (!data || data.ok === false) {
    showEmpty(list, data && data.error ? data.error : "Unable to load agreements");
    return;
  }
  const proposals = data.proposals || [];
  if (!proposals.length) {
    showEmpty(list, "No pending proposals.");
    return;
  }
  const listWrap = document.createElement("div");
  listWrap.className = "list";
  proposals.forEach((proposal) => {
    const item = document.createElement("div");
    item.className = "list-item agreement-item";
    const title = document.createElement("div");
    title.className = "list-title";
    title.textContent = proposal.title || "Team memory proposal";
    const meta = document.createElement("div");
    meta.className = "list-meta";
    const parts = [];
    if (proposal.status) parts.push(`status: ${proposal.status}`);
    if (proposal.status_line) parts.push(proposal.status_line);
    if (proposal.approval_required !== undefined && proposal.approval_count !== undefined) {
      parts.push(`approvals: ${proposal.approval_count} of ${proposal.approval_required}`);
    }
    if (proposal.proposed_by) parts.push(`by: ${proposal.proposed_by}`);
    if (proposal.phase_id) parts.push(`phase: ${proposal.phase_id}`);
    if (proposal.preview) parts.push(`preview: ${proposal.preview}`);
    meta.textContent = parts.join(" · ");
    const actions = document.createElement("div");
    actions.className = "list-actions";
    const approveBtn = document.createElement("button");
    approveBtn.className = "btn ghost small";
    approveBtn.textContent = "Approve";
    approveBtn.onclick = () => applyAgreementAction("approve", proposal.proposal_id);
    const rejectBtn = document.createElement("button");
    rejectBtn.className = "btn ghost small";
    rejectBtn.textContent = "Reject";
    rejectBtn.onclick = () => applyAgreementAction("reject", proposal.proposal_id);
    actions.appendChild(approveBtn);
    actions.appendChild(rejectBtn);
    item.appendChild(title);
    item.appendChild(meta);
    item.appendChild(actions);
    listWrap.appendChild(item);
  });
  list.appendChild(listWrap);
}
async function refreshAgreements() {
  if (traceLaneMode !== "team") {
    renderAgreements(cachedAgreements);
    return;
  }
  const data = await fetchJson("/api/memory/agreements");
  renderAgreements(data);
}
async function applyAgreementAction(action, proposalId) {
  const res = await fetch(`/api/memory/agreements/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ proposal_id: proposalId }),
  });
  const data = await res.json();
  if (!data.ok) {
    showToast("Agreement action failed.");
    if (data.error) showToast(data.error);
    return;
  }
  if (Array.isArray(data.traces) && data.traces.length) {
    cachedTraces = cachedTraces.concat(data.traces);
    renderTraces(cachedTraces);
  }
  renderAgreements(data);
}
function collectEventsForIds(map, ids) {
  const events = [];
  if (!map || !ids) return events;
  ids.forEach((memoryId) => {
    const event = map.get(memoryId);
    if (event) events.push(event);
  });
  return events;
}
function collectImpactEventsByDepth(map, ids) {
  const byDepth = new Map();
  if (!map || !ids) return byDepth;
  ids.forEach((memoryId) => {
    const entry = map.get(memoryId);
    if (!entry) return;
    Object.keys(entry).forEach((depth) => {
      const event = entry[depth];
      if (!event) return;
      const events = byDepth.get(depth) || [];
      events.push(event);
      byDepth.set(depth, events);
    });
  });
  return byDepth;
}
function memoryIdsForEvent(event) {
  if (!event || typeof event !== "object") return [];
  if (typeof event.memory_id === "string") return [event.memory_id];
  if (typeof event.to_id === "string") return [event.to_id];
  if (typeof event.winner_id === "string") return [event.winner_id];
  if (typeof event.from_id === "string") return [event.from_id];
  if (Array.isArray(event.written)) {
    return event.written.map((item) => item && item.id).filter((value) => typeof value === "string");
  }
  return [];
}
function formatExplanationText(explainEvent) {
  const lines = [];
  if (explainEvent.title) lines.push(explainEvent.title);
  const detail = Array.isArray(explainEvent.lines) ? explainEvent.lines : [];
  detail.forEach((line) => {
    if (line) lines.push(line);
  });
  return lines.join("\n");
}
function formatLinksText(linkEvents) {
  const lines = [];
  linkEvents.forEach((event) => {
    if (event.memory_id) {
      lines.push(`Memory id is ${event.memory_id}.`);
    }
    const detail = Array.isArray(event.lines) ? event.lines : [];
    detail.forEach((line) => {
      if (line) lines.push(line);
    });
  });
  return lines.join("\n");
}
function formatPathText(pathEvents) {
  const lines = [];
  pathEvents.forEach((event) => {
    if (event.title) lines.push(event.title);
    if (event.memory_id) {
      lines.push(`Memory id is ${event.memory_id}.`);
    }
    const detail = Array.isArray(event.lines) ? event.lines : [];
    detail.forEach((line) => {
      if (line) lines.push(line);
    });
  });
  return lines.join("\n");
}
function formatImpactText(impactEvents) {
  const lines = [];
  impactEvents.forEach((event) => {
    if (event.title) lines.push(event.title);
    if (event.memory_id) {
      lines.push(`Memory id is ${event.memory_id}.`);
    }
    const detail = Array.isArray(event.lines) ? event.lines : [];
    detail.forEach((line) => {
      if (line) lines.push(line);
    });
    const pathDetail = Array.isArray(event.path_lines) ? event.path_lines : [];
    pathDetail.forEach((line) => {
      if (line) lines.push(line);
    });
  });
  return lines.join("\n");
}
function defaultImpactDepth(impactByDepth) {
  if (!impactByDepth || impactByDepth.size === 0) return null;
  if (impactByDepth.has("1")) return "1";
  if (impactByDepth.has("2")) return "2";
  const keys = Array.from(impactByDepth.keys()).sort();
  return keys[0] || null;
}
function appendImpactControls(block, label, impactByDepth) {
  if (!impactByDepth || impactByDepth.size === 0) return;
  const impactBtn = document.createElement("button");
  impactBtn.className = "btn ghost small";
  impactBtn.textContent = "Impact";
  label.appendChild(impactBtn);

  const impactWrapper = document.createElement("div");
  impactWrapper.className = "trace-impact";
  impactWrapper.style.display = "none";

  const depthRow = document.createElement("div");
  depthRow.className = "trace-impact-depth";
  const depth1Btn = document.createElement("button");
  depth1Btn.className = "btn ghost small";
  depth1Btn.textContent = "Depth 1";
  const depth2Btn = document.createElement("button");
  depth2Btn.className = "btn ghost small";
  depth2Btn.textContent = "Depth 2";
  depthRow.appendChild(depth1Btn);
  depthRow.appendChild(depth2Btn);

  const impactBlock = createCodeBlock("");
  impactBlock.classList.add("trace-links");

  const updateDepth = (depthKey) => {
    const events = impactByDepth.get(depthKey) || [];
    impactBlock.textContent = formatImpactText(events);
    depth1Btn.classList.toggle("toggle-active", depthKey === "1");
    depth2Btn.classList.toggle("toggle-active", depthKey === "2");
  };

  const initialDepth = defaultImpactDepth(impactByDepth);
  if (initialDepth) {
    updateDepth(initialDepth);
  }

  depth1Btn.disabled = !impactByDepth.has("1");
  depth2Btn.disabled = !impactByDepth.has("2");

  depth1Btn.onclick = () => updateDepth("1");
  depth2Btn.onclick = () => updateDepth("2");
  impactBtn.onclick = () => {
    const nextState = impactWrapper.style.display === "none" ? "block" : "none";
    impactWrapper.style.display = nextState;
  };

  impactWrapper.appendChild(depthRow);
  impactWrapper.appendChild(impactBlock);
  block.appendChild(impactWrapper);
}
function renderPlainTraceValue(value) {
  if (Array.isArray(value) || (value && typeof value === "object")) {
    return formatPlainTrace(value);
  }
  return formatPlainScalar(value);
}
function currentPhaseIdForTrace(trace) {
  const events = trace.canonical_events || [];
  const recall = events.find((event) => event && event.type === "memory_recall");
  if (recall && recall.current_phase && recall.current_phase.phase_id) {
    return recall.current_phase.phase_id;
  }
  const phaseEvent = events.find((event) => event && event.type === "memory_phase_started");
  if (phaseEvent && phaseEvent.phase_id) {
    return phaseEvent.phase_id;
  }
  return null;
}
function filterMemoryEventForPhase(event, phaseId, mode) {
  if (!event || mode !== "current" || !phaseId) return event;
  if (event.type === "memory_recall" && Array.isArray(event.recalled)) {
    const filtered = event.recalled.filter((item) => item && item.meta && item.meta.phase_id === phaseId);
    if (filtered.length === event.recalled.length) return event;
    const next = { ...event, recalled: filtered };
    return next;
  }
  if (event.phase_id && event.phase_id !== phaseId) return null;
  return event;
}
function filterMemoryEventForLane(event, laneMode) {
  if (!event || !laneMode) return event;
  if (event.type === "memory_recall" && Array.isArray(event.recalled)) {
    const filtered = event.recalled.filter((item) => item && item.meta && item.meta.lane === laneMode);
    if (!filtered.length) return null;
    const next = { ...event, recalled: filtered };
    return next;
  }
  if (event.type === "memory_write" && Array.isArray(event.written)) {
    const filtered = event.written.filter((item) => item && item.meta && item.meta.lane === laneMode);
    if (!filtered.length) return null;
    const next = { ...event, written: filtered };
    return next;
  }
  if (event.type === "memory_denied" && event.attempted && event.attempted.meta) {
    if (event.attempted.meta.lane !== laneMode) return null;
    return event;
  }
  if (event.type === "memory_team_summary") {
    return laneMode === "team" ? event : null;
  }
  if (event.lane) {
    return event.lane === laneMode ? event : null;
  }
  if (event.from_lane || event.to_lane) {
    if (event.from_lane === laneMode || event.to_lane === laneMode) return event;
    return null;
  }
  return event;
}
  function matchTrace(trace, needle) {
    if (!needle) return true;
    const eventTypes = (trace.canonical_events || []).map((event) => event.type).join(" ");
    const values = [trace.provider, trace.model, trace.ai_name, trace.ai_profile_name, trace.agent_name, trace.input, trace.output, trace.result, eventTypes]
      .map((v) => (typeof v === "string" ? v : v ? JSON.stringify(v) : ""))
      .join(" ")
      .toLowerCase();
    return values.includes(needle);
  }
  function renderTraces(data) {
  cachedTraces = Array.isArray(data) ? data : cachedTraces;
  selectedTrace = null;
  const container = document.getElementById("traces"); if (!container) return; container.innerHTML = "";
  const filtered = cachedTraces.filter((t) => matchTrace(t, traceFilterText));
  const traces = filtered.slice().reverse();
  if (!traces.length) {
    const message = cachedTraces.length ? "No traces match filter." : "No traces yet — run a flow to generate traces.";
    showEmpty(container, message);
    updateCopyButton("tracesCopy", () => "[]");
    updateTraceCopyButtons();
    return;
  }
  const list = document.createElement("div");
  list.className = "list";
  traces.forEach((trace, idx) => {
    const row = document.createElement("div");
    row.className = "trace-row";
    const header = document.createElement("div");
    header.className = "trace-header";
    const title = document.createElement("div");
    title.className = "trace-title";
    title.textContent = `Trace #${traces.length - idx}`;
    const meta = document.createElement("div");
    meta.className = "trace-meta";
    const model = trace.model ? `model: ${trace.model}` : undefined;
    const aiName = trace.ai_name ? `ai: ${trace.ai_name}` : undefined;
    const status = trace.error ? "status: error" : "status: ok";
    meta.textContent = [model, aiName, status].filter(Boolean).join(" · ");
    header.appendChild(title);
    header.appendChild(meta);
    const details = document.createElement("div");
    details.className = "trace-details";
    if (trace.type === "parallel_agents" && Array.isArray(trace.agents)) {
      appendTraceSection(details, "Agents", trace.agents, false, traceRenderMode);
    } else {
      appendTraceSection(details, "Input", trace.input, false, traceRenderMode);
      appendTraceSection(details, "Memory", trace.memory, false, traceRenderMode);
      const phaseId = currentPhaseIdForTrace(trace);
      appendMemoryEventsSection(details, trace, phaseId, traceRenderMode);
      appendTraceSection(details, "Tool calls", trace.tool_calls, false, traceRenderMode);
      appendTraceSection(details, "Tool results", trace.tool_results, false, traceRenderMode);
      appendTraceSection(details, "Output", trace.output ?? trace.result, true, traceRenderMode);
    }
    row.appendChild(header);
    row.appendChild(details);
    header.onclick = () => {
      row.classList.toggle("open");
      selectedTrace = trace;
      updateTraceCopyButtons();
    };
    list.appendChild(row);
  });
  container.appendChild(list);
  updateCopyButton("tracesCopy", () => JSON.stringify(cachedTraces || [], null, 2));
  updateTraceCopyButtons();
  renderAgreements(cachedAgreements);
}
async function executeAction(actionId, payload) {
  const res = await fetch("/api/action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: actionId, payload }),
  });
  const data = await res.json();
  if (!data.ok) {
    showToast("Action failed safely.");
    if (data.error) showToast(data.error);
  }
  if (!data.ok && data.errors) {
    return data;
  }
  if (data.state) {
    renderState(data.state);
  }
  if (data.traces) {
    renderTraces(data.traces);
    refreshAgreements();
  }
  if (data.ui) {
    cachedManifest = data.ui;
    renderUI(data.ui);
    const setting = (cachedManifest.theme && cachedManifest.theme.setting) || "system";
    const runtime = (cachedManifest.theme && cachedManifest.theme.current) || setting;
    themeSetting = setting;
    runtimeTheme = runtime;
    const currentTheme = themeOverride || runtime;
    applyTheme(currentTheme);
    applyThemeTokens(cachedManifest.theme && cachedManifest.theme.tokens ? cachedManifest.theme.tokens : {}, currentTheme);
    const selector = document.getElementById("themeSelect");
    if (selector) selector.value = themeOverride || setting;
  }
  reselectElement();
  return data;
}
async function performEdit(op, elementId, pageName, value, targetExtras = {}) {
  const res = await fetch("/api/edit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ op, target: { element_id: elementId, page: pageName, ...targetExtras }, value }),
  });
  const data = await res.json();
  if (!data.ok) {
    showToast(data.error || "Edit failed");
    return;
  }
  renderSummary(data.summary);
  renderActions(data.actions);
  renderLint(data.lint);
  if (data.ui) {
    cachedManifest = data.ui;
    renderUI(data.ui);
  }
  reselectElement();
}
async function refreshAll() {
  const [summary, ui, actions, lint, tools, packs, security] = await Promise.all([
    fetchJson("/api/summary"),
    fetchJson("/api/ui"),
    fetchJson("/api/actions"),
    fetchJson("/api/lint"),
    fetchJson("/api/tools"),
    fetchJson("/api/packs"),
    fetchJson("/api/security"),
  ]);
  renderSummary(summary);
  renderActions(actions);
  renderLint(lint);
  renderTools(tools);
  renderPacks(packs);
  renderSecurity(security);
  renderState({});
  renderTraces([]);
  if (ui.ok !== false) {
    cachedManifest = ui;
    renderUI(ui);
  } else {
    const uiContainer = document.getElementById("ui");
    showEmpty(uiContainer, ui.error || "Unable to load UI");
  }
  const setting = (cachedManifest && cachedManifest.theme && cachedManifest.theme.setting) || "system";
  const runtime = (cachedManifest && cachedManifest.theme && cachedManifest.theme.current) || setting;
  themeSetting = setting;
  runtimeTheme = runtime;
  preferencePolicy = (cachedManifest && cachedManifest.theme && cachedManifest.theme.preference) || preferencePolicy;
  const currentTheme = themeOverride || runtime;
  applyTheme(currentTheme);
  const activeTokens = (cachedManifest && cachedManifest.theme && cachedManifest.theme.tokens) || {};
  applyThemeTokens(activeTokens, currentTheme);
  const selector = document.getElementById("themeSelect");
  if (selector) {
    selector.value = themeOverride || runtime || setting;
    selector.disabled = !preferencePolicy.allow_override;
  }
  seedActionId = detectSeedAction(cachedManifest, actions);
  toggleSeed(seedActionId);
  applyLocalPreferenceIfNeeded();
  renderTruthBar(cachedManifest);
  reselectElement();
  if (window.refreshGraphPanel) window.refreshGraphPanel();
  if (window.refreshTrustPanel) window.refreshTrustPanel();
  if (window.refreshDataPanel) window.refreshDataPanel();
  if (window.refreshFixPanel) window.refreshFixPanel();
  refreshAgreements();
}
function setupTabs() {
  const tabs = Array.from(document.querySelectorAll(".tab"));
  const panels = Array.from(document.querySelectorAll(".panel[data-tab]"));
  const setActive = (name) => {
    tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === name));
    panels.forEach((panel) => panel.classList.toggle("active", panel.dataset.tab === name));
  };
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => setActive(tab.dataset.tab));
  });
  setActive("summary");
}
function setupTraceFilter() {
  const input = document.getElementById("tracesFilter");
  if (!input) return;
  input.addEventListener("input", () => {
    if (traceFilterTimer) clearTimeout(traceFilterTimer);
    traceFilterTimer = setTimeout(() => {
      traceFilterText = input.value.trim().toLowerCase();
      renderTraces(cachedTraces);
    }, 120);
  });
}
function setupTraceFormatToggle() {
  const plainBtn = document.getElementById("traceFormatPlain");
  const jsonBtn = document.getElementById("traceFormatJson");
  if (!plainBtn || !jsonBtn) return;
  const applyMode = (mode) => {
    traceRenderMode = mode;
    plainBtn.classList.toggle("toggle-active", mode === "plain");
    jsonBtn.classList.toggle("toggle-active", mode === "json");
    plainBtn.setAttribute("aria-pressed", mode === "plain");
    jsonBtn.setAttribute("aria-pressed", mode === "json");
    renderTraces(cachedTraces);
  };
  plainBtn.onclick = () => applyMode("plain");
  jsonBtn.onclick = () => applyMode("json");
  applyMode(traceRenderMode || "plain");
}
function setupTracePhaseToggle() {
  const currentBtn = document.getElementById("tracePhaseCurrent");
  const historyBtn = document.getElementById("tracePhaseHistory");
  if (!currentBtn || !historyBtn) return;
  const applyMode = (mode) => {
    tracePhaseMode = mode;
    currentBtn.classList.toggle("toggle-active", mode === "current");
    historyBtn.classList.toggle("toggle-active", mode === "history");
    currentBtn.setAttribute("aria-pressed", mode === "current");
    historyBtn.setAttribute("aria-pressed", mode === "history");
    renderTraces(cachedTraces);
  };
  currentBtn.onclick = () => applyMode("current");
  historyBtn.onclick = () => applyMode("history");
  applyMode(tracePhaseMode || "current");
}
function setupTraceLaneToggle() {
  const myBtn = document.getElementById("traceLaneMy");
  const teamBtn = document.getElementById("traceLaneTeam");
  const systemBtn = document.getElementById("traceLaneSystem");
  if (!myBtn || !teamBtn || !systemBtn) return;
  const applyMode = (mode) => {
    traceLaneMode = mode;
    myBtn.classList.toggle("toggle-active", mode === "my");
    teamBtn.classList.toggle("toggle-active", mode === "team");
    systemBtn.classList.toggle("toggle-active", mode === "system");
    myBtn.setAttribute("aria-pressed", mode === "my");
    teamBtn.setAttribute("aria-pressed", mode === "team");
    systemBtn.setAttribute("aria-pressed", mode === "system");
    renderTraces(cachedTraces);
    refreshAgreements();
  };
  myBtn.onclick = () => applyMode("my");
  teamBtn.onclick = () => applyMode("team");
  systemBtn.onclick = () => applyMode("system");
  applyMode(traceLaneMode || "my");
}
function setupToolsFilter() {
  const input = document.getElementById("toolsFilter");
  if (!input) return;
  input.addEventListener("input", () => {
    if (toolsFilterTimer) clearTimeout(toolsFilterTimer);
    toolsFilterTimer = setTimeout(() => {
      toolsFilterText = input.value.trim().toLowerCase();
      renderTools(cachedTools);
    }, 120);
  });
}
function detectSeedAction(manifest, actionsPayload) {
  const preferred = ["seed", "seed_data", "seed_demo", "demo_seed", "seed_customers"];
  const actions = actionsPayload?.actions || Object.values(manifest?.actions || {});
  const callFlows = actions.filter((a) => a.type === "call_flow");
  for (const name of preferred) {
    const found = callFlows.find((a) => a.flow === name);
    if (found) return found.id || found.action_id || `action.${name}`;
  }
  return callFlows.length ? callFlows[0].id || callFlows[0].action_id || null : null;
}
function toggleSeed(actionId) {
  const btn = document.getElementById("seed");
  if (!btn) return;
  if (actionId) btn.classList.remove("hidden");
  else btn.classList.add("hidden");
}
const seedButton = document.getElementById("seed");
if (seedButton) {
  seedButton.onclick = async () => {
    if (!seedActionId) {
      showToast("No seed action found.");
      return;
    }
    await executeAction(seedActionId, {});
    refreshAll();
  };
}
async function loadVersion() {
  try {
    const data = await fetchJson("/api/version");
    if (data && data.ok && data.version) {
      setVersionLabel(data.version);
    }
  } catch (err) {
    setVersionLabel("");
  }
}
window.reselectElement = function () {
  if (!selectedElementId || !cachedManifest) {
    renderInspector(null, null);
    return;
  }
  const match = findElementInManifest(selectedElementId);
  if (!match) {
    renderInspector(null, null);
    return;
  }
  selectedElement = match.element;
  selectedPage = match.page;
  renderInspector(selectedElement, selectedPage);
  document.querySelectorAll(".ui-element").forEach((el) => {
    el.classList.toggle("selected", el.dataset.elementId === selectedElementId);
  });
};

document.getElementById("refresh").onclick = refreshAll;
document.getElementById("reset").onclick = async () => {
  const persistence = getPersistenceInfo();
  const resetPath = persistence.path ? ` in ${persistence.path}` : "";
  const prompt =
    persistence.kind === "sqlite" && persistence.enabled
      ? `Reset will clear persisted records/state${resetPath}. Continue?`
      : "Reset will clear state and records for this session. Continue?";
  const ok = window.confirm(prompt);
  if (!ok) return;
  await fetch("/api/reset", { method: "POST", body: "{}" });
  renderState({});
  renderTraces([]);
  refreshAll();
};
const themeSelect = document.getElementById("themeSelect");
if (themeSelect) {
  themeSelect.onchange = (e) => {
    const value = e.target.value;
    if (!preferencePolicy.allow_override) {
      themeOverride = value;
      applyTheme(value);
      const tokens = (cachedManifest && cachedManifest.theme && cachedManifest.theme.tokens) || {};
      applyThemeTokens(tokens, value);
      renderTruthBar(cachedManifest);
      renderSummary(cachedSummary);
      if (cachedManifest) {
        renderUI(cachedManifest);
        reselectElement();
      }
      return;
    }
    themeOverride = null;
    updateRuntimeTheme(value, preferencePolicy.persist);
  };
}
setupTabs();
setupTraceFilter();
setupTraceFormatToggle();
setupTracePhaseToggle();
setupTraceLaneToggle();
setupToolsFilter();
loadVersion();
const helpButton = document.getElementById("helpButton");
const helpModal = document.getElementById("helpModal");
const helpClose = document.getElementById("helpClose");
if (helpButton && helpModal && helpClose) {
  helpButton.onclick = () => helpModal.classList.remove("hidden");
  helpClose.onclick = () => helpModal.classList.add("hidden");
  helpModal.addEventListener("click", (e) => {
    if (e.target === helpModal) {
      helpModal.classList.add("hidden");
    }
  });
}
const toolsAutoBind = document.getElementById("toolsAutoBind");
if (toolsAutoBind) {
  toolsAutoBind.onclick = async () => {
    try {
      const resp = await fetch("/api/tools/auto-bind", { method: "POST", body: "{}" });
      const data = await resp.json();
      if (data.ok) {
        const count = (data.missing_bound || []).length;
        showToast(count ? `Auto-bound ${count} tools.` : "No missing bindings.");
        refreshAll();
        return;
      }
      showToast(data.error || "Auto-bind failed.");
    } catch (err) {
      showToast("Auto-bind failed.");
    }
  };
}
const toolsOpenWizard = document.getElementById("toolsOpenWizard");
if (toolsOpenWizard) {
  toolsOpenWizard.onclick = () => {
    const btn = document.getElementById("toolWizardButton");
    if (btn) btn.click();
  };
}
const toolsFixToggle = document.getElementById("toolsFixToggle");
if (toolsFixToggle) {
  toolsFixToggle.onclick = () => {
    const panel = document.getElementById("toolsFixPanel");
    if (!panel) return;
    panel.classList.toggle("hidden");
  };
}
const packsRefresh = document.getElementById("packsRefresh");
if (packsRefresh) {
  packsRefresh.onclick = () => refreshAll();
}
const securityRefresh = document.getElementById("securityRefresh");
if (securityRefresh) {
  securityRefresh.onclick = () => refreshSecurity();
}
const packsAdd = document.getElementById("packsAdd");
if (packsAdd) {
  packsAdd.onclick = async () => {
    const input = document.getElementById("packsPath");
    const path = input ? input.value.trim() : "";
    if (!path) {
      showToast("Pack path required.");
      return;
    }
    try {
      const resp = await fetch("/api/packs/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      const data = await resp.json();
      if (!data.ok) {
        showToast(data.error || "Pack add failed.");
        return;
      }
      if (input) input.value = "";
      showToast("Pack installed.");
      refreshAll();
    } catch (err) {
      showToast("Pack add failed.");
    }
  };
}
refreshAll();
