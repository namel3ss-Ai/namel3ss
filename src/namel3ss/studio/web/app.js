let cachedSummary = {};
let cachedState = {};
let cachedActions = {};
let cachedTraces = [];
let cachedLint = {};
let cachedManifest = null;
let traceFilterText = "";
let traceFilterTimer = null;
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
    row.innerHTML = `<div class="kv-label">theme</div><div class="kv-value">setting: ${setting}, runtime: ${runtime}, effective: ${effective}${overrideLabel}</div>`;
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
function appendTraceSection(details, label, value, copyable = false) {
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
  wrapper.appendChild(createCodeBlock(value));
  details.appendChild(wrapper);
}
  function matchTrace(trace, needle) {
    if (!needle) return true;
    const values = [trace.provider, trace.model, trace.ai_name, trace.ai_profile_name, trace.agent_name, trace.input, trace.output, trace.result]
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
      appendTraceSection(details, "Agents", trace.agents);
    } else {
      appendTraceSection(details, "Input", trace.input);
      appendTraceSection(details, "Memory", trace.memory);
      appendTraceSection(details, "Tool calls", trace.tool_calls);
      appendTraceSection(details, "Tool results", trace.tool_results);
      appendTraceSection(details, "Output", trace.output ?? trace.result, true);
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
  const [summary, ui, actions, lint] = await Promise.all([
    fetchJson("/api/summary"),
    fetchJson("/api/ui"),
    fetchJson("/api/actions"),
    fetchJson("/api/lint"),
  ]);
  renderSummary(summary);
  renderActions(actions);
  renderLint(lint);
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
refreshAll();
