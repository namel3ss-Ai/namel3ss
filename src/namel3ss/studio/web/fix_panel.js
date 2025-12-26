(() => {
let cachedFix = {
  diagnostics: [],
  preview: [],
  pendingEdits: [],
  selectedDiagnostic: null,
};

function setupFixPanel() {
  const refreshButton = document.getElementById("fixRefresh");
  if (refreshButton) {
    refreshButton.onclick = () => refreshFixPanel();
  }
}

async function refreshFixPanel() {
  const container = document.getElementById("fixDiagnostics");
  if (container) {
    container.innerHTML = "";
    showStatus(container, "Loading diagnostics…", "loading");
  }
  try {
    const resp = await postJson("/api/editor/diagnose", {});
    cachedFix.diagnostics = resp.diagnostics || [];
    cachedFix.preview = [];
    cachedFix.pendingEdits = [];
    cachedFix.selectedDiagnostic = null;
    renderFixDiagnostics(cachedFix.diagnostics);
    renderFixPreview([]);
    renderFixRename();
  } catch (err) {
    if (container) {
      showStatus(container, "Unable to load diagnostics.", "error");
    }
  }
}

function renderFixDiagnostics(diagnostics) {
  const container = document.getElementById("fixDiagnostics");
  if (!container) return;
  container.innerHTML = "";
  container.appendChild(buildSectionHeader("Diagnostics"));
  if (!diagnostics || !diagnostics.length) {
    showEmpty(container, "No diagnostics 🎉");
    return;
  }
  diagnostics.forEach((diag) => {
    const row = document.createElement("div");
    row.className = "fix-diagnostic";
    row.onclick = () => {
      cachedFix.selectedDiagnostic = diag;
      fillRenameFromDiagnostic(diag);
    };
    const filePart = diag.file ? `${diag.file}:${diag.line || ""}` : "unknown file";
    row.innerHTML = `
      <div><strong>${diag.severity || ""}</strong> ${diag.id || ""}</div>
      <div class=\"list-meta\">${diag.message || ""}</div>
      <div class=\"list-meta\">${filePart}</div>
    `;
    if (diag.fix_available) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn secondary small";
      button.textContent = "Fix";
      button.onclick = async (event) => {
        event.stopPropagation();
        await requestFix(diag);
      };
      row.appendChild(button);
    }
    container.appendChild(row);
  });
}

async function requestFix(diag) {
  if (!diag || !diag.file || !diag.id) {
    showToast("Diagnostic missing file or id.");
    return;
  }
  try {
    const resp = await postJson("/api/editor/fix", {
      file: diag.file,
      diagnostic_id: diag.id,
    });
    cachedFix.preview = resp.preview || [];
    cachedFix.pendingEdits = resp.edits || [];
    renderFixPreview(cachedFix.preview);
  } catch (err) {
    showToast("Fix request failed.");
  }
}

function renderFixPreview(preview) {
  const container = document.getElementById("fixPreview");
  if (!container) return;
  container.innerHTML = "";
  const header = buildSectionHeader("Preview", [
    buildButton("Apply", "primary", applyPendingFixes, true),
    buildButton("Clear", "ghost", clearFixPreview, true),
  ]);
  container.appendChild(header);
  const applyButton = header.querySelector(".btn.primary");
  if (applyButton) applyButton.disabled = !cachedFix.pendingEdits.length;
  if (!preview || !preview.length) {
    showEmpty(container, "Select a fix or rename to preview changes.");
    return;
  }
  preview.forEach((entry) => {
    const label = document.createElement("div");
    label.className = "fix-preview-file";
    label.textContent = entry.file || "file";
    container.appendChild(label);
    const diffBlock = createCodeBlock(entry.diff || "");
    container.appendChild(diffBlock);
  });
}

function renderFixRename() {
  const container = document.getElementById("fixRename");
  if (!container) return;
  container.innerHTML = "";
  container.appendChild(buildSectionHeader("Rename"));
  const row = document.createElement("div");
  row.className = "fix-rename-row";
  row.innerHTML = `
    <input id=\"renameFile\" type=\"text\" placeholder=\"file path\" aria-label=\"Rename file\">
    <input id=\"renameLine\" type=\"number\" min=\"1\" placeholder=\"line\" aria-label=\"Rename line\">
    <input id=\"renameColumn\" type=\"number\" min=\"1\" placeholder=\"column\" aria-label=\"Rename column\">
    <input id=\"renameNewName\" type=\"text\" placeholder=\"new name\" aria-label=\"Rename new name\">
  `;
  container.appendChild(row);
  const actionRow = document.createElement("div");
  actionRow.className = "fix-preview-actions";
  const previewButton = buildButton("Preview rename", "secondary", requestRename, true);
  actionRow.appendChild(previewButton);
  container.appendChild(actionRow);
}

function fillRenameFromDiagnostic(diag) {
  if (!diag) return;
  const fileInput = document.getElementById("renameFile");
  const lineInput = document.getElementById("renameLine");
  const columnInput = document.getElementById("renameColumn");
  if (fileInput && diag.file) fileInput.value = diag.file;
  if (lineInput && diag.line) lineInput.value = diag.line;
  if (columnInput && diag.column) columnInput.value = diag.column;
}

async function requestRename() {
  const file = document.getElementById("renameFile");
  const line = document.getElementById("renameLine");
  const column = document.getElementById("renameColumn");
  const newName = document.getElementById("renameNewName");
  if (!file || !line || !column || !newName) return;
  const payload = {
    file: file.value.trim(),
    position: {
      line: parseInt(line.value || "0", 10),
      column: parseInt(column.value || "0", 10),
    },
    new_name: newName.value.trim(),
  };
  if (!payload.file || !payload.position.line || !payload.position.column || !payload.new_name) {
    showToast("Rename requires file, line, column, and new name.");
    return;
  }
  try {
    const resp = await postJson("/api/editor/rename", payload);
    cachedFix.preview = resp.preview || [];
    cachedFix.pendingEdits = resp.edits || [];
    renderFixPreview(cachedFix.preview);
  } catch (err) {
    showToast("Rename failed.");
  }
}

async function applyPendingFixes() {
  if (!cachedFix.pendingEdits.length) {
    showToast("No pending edits.");
    return;
  }
  try {
    const resp = await postJson("/api/editor/apply", { edits: cachedFix.pendingEdits });
    cachedFix.pendingEdits = [];
    cachedFix.preview = [];
    cachedFix.diagnostics = resp.diagnostics || [];
    renderFixDiagnostics(cachedFix.diagnostics);
    renderFixPreview([]);
    showToast("Changes applied.");
  } catch (err) {
    showToast("Apply failed.");
  }
}

function clearFixPreview() {
  cachedFix.pendingEdits = [];
  cachedFix.preview = [];
  renderFixPreview([]);
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

setupFixPanel();
refreshFixPanel();
window.refreshFixPanel = refreshFixPanel;
})();
