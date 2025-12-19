let cachedSummary = {};
let cachedState = {};
let cachedActions = {};
let cachedTraces = [];
let cachedLint = {};
let traceFilterText = "";
let traceFilterTimer = null;
let selectedTrace = null;
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
  const values = [
    trace.provider,
    trace.model,
    trace.ai_name,
    trace.ai_profile_name,
    trace.agent_name,
    trace.input,
    trace.output,
    trace.result,
  ]
    .map((v) => (typeof v === "string" ? v : v ? JSON.stringify(v) : ""))
    .join(" ")
    .toLowerCase();
  return values.includes(needle);
}
function updateTraceCopyButtons() {
  const outputBtn = document.getElementById("traceCopyOutput");
  const jsonBtn = document.getElementById("traceCopyJson");
  const has = !!selectedTrace;
  [outputBtn, jsonBtn].forEach((btn) => {
    if (!btn) return;
    btn.disabled = !has;
  });
  if (outputBtn) {
    outputBtn.onclick = () => {
      if (selectedTrace) copyText(selectedTrace.output ?? selectedTrace.result ?? "");
    };
  }
  if (jsonBtn) {
    jsonBtn.onclick = () => {
      if (selectedTrace) copyText(selectedTrace);
    };
  }
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
  if (!data.ok && data.error) {
    alert(data.error);
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
    renderUI(data.ui);
  }
  return data;
}
async function performEdit(op, elementId, pageName, value) {
  const res = await fetch("/api/edit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ op, target: { element_id: elementId, page: pageName }, value }),
  });
  const data = await res.json();
  if (!data.ok) {
    alert(data.error || "Edit failed");
    return;
  }
  renderSummary(data.summary);
  renderActions(data.actions);
  renderLint(data.lint);
  if (data.ui) {
    renderUI(data.ui);
  }
}
function renderUI(manifest) {
  const select = document.getElementById("pageSelect");
  const uiContainer = document.getElementById("ui");
  const pages = manifest.pages || [];
  const currentSelection = select.value;
  select.innerHTML = "";
  pages.forEach((p, idx) => {
    const opt = document.createElement("option");
    opt.value = p.name;
    opt.textContent = p.name;
    if (p.name === currentSelection || (currentSelection === "" && idx === 0)) {
      opt.selected = true;
    }
    select.appendChild(opt);
  });
  function renderPage(pageName) {
    uiContainer.innerHTML = "";
    const page = pages.find((p) => p.name === pageName) || pages[0];
    if (!page) {
      showEmpty(uiContainer, "No pages");
      return;
    }
    page.elements.forEach((el) => {
      const wrapper = document.createElement("div");
      wrapper.className = "ui-element";
      if (el.type === "title") {
        const h = document.createElement("h3");
        h.textContent = el.value;
        wrapper.appendChild(h);
        const actions = document.createElement("div");
        actions.className = "ui-buttons";
        const edit = document.createElement("button");
        edit.className = "btn ghost small";
        edit.textContent = "Edit";
        edit.onclick = () => showEditField(el, page.name, "set_title");
        actions.appendChild(edit);
        wrapper.appendChild(actions);
      } else if (el.type === "text") {
        const p = document.createElement("p");
        p.textContent = el.value;
        wrapper.appendChild(p);
        const actions = document.createElement("div");
        actions.className = "ui-buttons";
        const edit = document.createElement("button");
        edit.className = "btn ghost small";
        edit.textContent = "Edit";
        edit.onclick = () => showEditField(el, page.name, "set_text");
        actions.appendChild(edit);
        wrapper.appendChild(actions);
      } else if (el.type === "button") {
        const actions = document.createElement("div");
        actions.className = "ui-buttons";
        const btn = document.createElement("button");
        btn.className = "btn primary";
        btn.textContent = el.label;
        btn.onclick = () => executeAction(el.action_id, {});
        actions.appendChild(btn);
        const rename = document.createElement("button");
        rename.className = "btn ghost small";
        rename.textContent = "Rename";
        rename.onclick = () => showEditField(el, page.name, "set_button_label");
        actions.appendChild(rename);
        wrapper.appendChild(actions);
      } else if (el.type === "form") {
        const formTitle = document.createElement("div");
        formTitle.className = "inline-label";
        formTitle.textContent = `Form: ${el.record}`;
        wrapper.appendChild(formTitle);
        const form = document.createElement("form");
        form.className = "ui-form";
        (el.fields || []).forEach((f) => {
          const label = document.createElement("label");
          label.textContent = f.name;
          const input = document.createElement("input");
          input.name = f.name;
          label.appendChild(input);
          form.appendChild(label);
        });
        const submit = document.createElement("button");
        submit.type = "submit";
        submit.className = "btn primary";
        submit.textContent = "Submit";
        form.appendChild(submit);
        const errors = document.createElement("div");
        errors.className = "errors";
        form.appendChild(errors);
        form.onsubmit = async (e) => {
          e.preventDefault();
          const values = {};
          (el.fields || []).forEach((f) => {
            const input = form.querySelector(`input[name="${f.name}"]`);
            values[f.name] = input ? input.value : "";
          });
          const result = await executeAction(el.action_id, { values });
          if (!result.ok && result.errors) {
            errors.textContent = result.errors.map((err) => `${err.field}: ${err.message}`).join("; ");
          } else if (!result.ok && result.error) {
            errors.textContent = result.error;
          } else {
            errors.textContent = "";
          }
        };
        wrapper.appendChild(form);
      } else if (el.type === "table") {
        const table = document.createElement("table");
        table.className = "ui-table";
        const header = document.createElement("tr");
        (el.columns || []).forEach((c) => {
          const th = document.createElement("th");
          th.textContent = c.name;
          header.appendChild(th);
        });
        table.appendChild(header);
        (el.rows || []).forEach((row) => {
          const tr = document.createElement("tr");
          (el.columns || []).forEach((c) => {
            const td = document.createElement("td");
            td.textContent = row[c.name] ?? "";
            tr.appendChild(td);
          });
          table.appendChild(tr);
        });
        wrapper.appendChild(table);
      }
      uiContainer.appendChild(wrapper);
    });
  }
  select.onchange = (e) => renderPage(e.target.value);
  const initialPage = select.value || (pages[0] ? pages[0].name : "");
  if (initialPage) {
    renderPage(initialPage);
  } else {
    showEmpty(uiContainer, "No pages");
  }
}
function showEditField(element, pageName, op) {
  const newValue = prompt("Enter new value", element.value || element.label || "");
  if (newValue === null) {
    return;
  }
  performEdit(op, element.element_id, pageName, newValue);
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
    renderUI(ui);
  } else {
    const uiContainer = document.getElementById("ui");
    showEmpty(uiContainer, ui.error || "Unable to load UI");
  }
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
document.getElementById("refresh").onclick = refreshAll;
document.getElementById("reset").onclick = async () => {
  await fetch("/api/reset", { method: "POST", body: "{}" });
  renderState({});
  renderTraces([]);
  refreshAll();
};
setupTabs();
setupTraceFilter();
refreshAll();
