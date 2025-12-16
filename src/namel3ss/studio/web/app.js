async function fetchJson(path, options) {
  const res = await fetch(path, options);
  return res.json();
}

function renderSummary(data) {
  const el = document.getElementById("summary");
  if (!data.ok) {
    el.textContent = data.error || "Error";
    return;
  }
  el.textContent = JSON.stringify(data.counts, null, 2);
}

function renderActions(data) {
  const el = document.getElementById("actions");
  if (!data.ok) {
    el.textContent = data.error || "Error";
    return;
  }
  el.textContent = data.actions
    .map((a) => {
      const parts = [a.id, a.type];
      if (a.flow) parts.push(`flow=${a.flow}`);
      if (a.record) parts.push(`record=${a.record}`);
      return parts.join("  ");
    })
    .join("\n");
}

function renderLint(data) {
  const el = document.getElementById("lint");
  if (!data.ok && data.error) {
    el.textContent = data.error;
    return;
  }
  el.textContent =
    data.findings
      .map((f) => `${f.severity} ${f.code} ${f.message} (${f.line}:${f.column})`)
      .join("\n") || "OK";
}

function renderState(data) {
  const el = document.getElementById("state");
  el.textContent = data ? JSON.stringify(data, null, 2) : "{}";
}

function renderTraces(data) {
  const el = document.getElementById("traces");
  el.textContent = data ? JSON.stringify(data, null, 2) : "[]";
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
    if (!page) return;
    page.elements.forEach((el) => {
      const div = document.createElement("div");
      div.className = "element";
      if (el.type === "title") {
        const h = document.createElement("h3");
        h.textContent = el.value;
        div.appendChild(h);
        const btn = document.createElement("button");
        btn.textContent = "Edit";
        btn.onclick = () => showEditField(el, page.name, "set_title");
        div.appendChild(btn);
      } else if (el.type === "text") {
        const p = document.createElement("p");
        p.textContent = el.value;
        div.appendChild(p);
        const btn = document.createElement("button");
        btn.textContent = "Edit";
        btn.onclick = () => showEditField(el, page.name, "set_text");
        div.appendChild(btn);
      } else if (el.type === "button") {
        const btn = document.createElement("button");
        btn.textContent = el.label;
        btn.onclick = () => executeAction(el.action_id, {});
        div.appendChild(btn);
        const rename = document.createElement("button");
        rename.textContent = "Rename";
        rename.onclick = () => showEditField(el, page.name, "set_button_label");
        div.appendChild(rename);
      } else if (el.type === "form") {
        const form = document.createElement("form");
        form.innerHTML = `<strong>Form: ${el.record}</strong>`;
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
        div.appendChild(form);
      } else if (el.type === "table") {
        const table = document.createElement("table");
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
        div.appendChild(table);
      }
      uiContainer.appendChild(div);
    });
  }

  select.onchange = (e) => renderPage(e.target.value);
  const initialPage = select.value || (pages[0] ? pages[0].name : "");
  if (initialPage) {
    renderPage(initialPage);
  } else {
    uiContainer.textContent = "No pages";
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
    document.getElementById("ui").textContent = ui.error || "Error";
  }
}

document.getElementById("refresh").onclick = refreshAll;
document.getElementById("reset").onclick = async () => {
  await fetch("/api/reset", { method: "POST", body: "{}" });
  renderState({});
  renderTraces([]);
  refreshAll();
};

refreshAll();
