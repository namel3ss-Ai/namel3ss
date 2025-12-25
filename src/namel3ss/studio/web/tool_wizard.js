function wizardEl(id) {
  return document.getElementById(id);
}

const wizardButton = wizardEl("toolWizardButton");
const wizardModal = wizardEl("toolWizardModal");
const wizardClose = wizardEl("toolWizardClose");
const wizardCancel = wizardEl("toolWizardCancel");
const wizardForm = wizardEl("toolWizardForm");
const wizardStatus = wizardEl("toolWizardStatus");
const wizardConflict = wizardEl("toolWizardConflict");
const wizardConflictMessage = wizardEl("toolWizardConflictMessage");
const wizardUseSuggestion = wizardEl("toolWizardUseSuggestion");
const wizardReuseExisting = wizardEl("toolWizardReuseExisting");
const wizardPreview = wizardEl("toolWizardPreview");
const wizardPreviewButton = wizardEl("toolWizardPreviewButton");

let wizardSuggestion = null;
let wizardHasPreview = false;
let wizardReuse = false;

function setWizardStatus(message, isError = false) {
  if (!wizardStatus) return;
  wizardStatus.textContent = message || "";
  wizardStatus.style.color = isError ? "#b00020" : "#333";
}

function setWizardPreview(content) {
  if (!wizardPreview) return;
  wizardPreview.textContent = content || "";
}

function markPreviewStale() {
  wizardHasPreview = false;
  wizardReuse = false;
  setWizardPreview("");
}

function showWizardModal() {
  if (!wizardModal) return;
  wizardModal.classList.remove("hidden");
  setWizardStatus("");
  setWizardPreview("");
  wizardHasPreview = false;
  wizardReuse = false;
  hideWizardConflict();
}

function hideWizardModal() {
  if (!wizardModal) return;
  wizardModal.classList.add("hidden");
  setWizardStatus("");
  setWizardPreview("");
  wizardHasPreview = false;
  wizardReuse = false;
  hideWizardConflict();
}

function hideWizardConflict() {
  if (!wizardConflict) return;
  wizardConflict.classList.add("hidden");
  if (wizardConflictMessage) wizardConflictMessage.textContent = "";
  wizardSuggestion = null;
}

function showWizardConflict(message, suggestion) {
  if (!wizardConflict) return;
  wizardConflict.classList.remove("hidden");
  if (wizardConflictMessage) wizardConflictMessage.textContent = message || "Tool already exists.";
  wizardSuggestion = suggestion || null;
}

async function submitWizard() {
  const payload = buildWizardPayload();
  if (!payload) return;
  if (!wizardHasPreview) {
    await requestWizardPreview(payload);
    return;
  }
  setWizardStatus("Creating tool...");
  try {
    const resp = await fetch("/api/tool-wizard", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, reuse_existing: wizardReuse }),
    });
    const data = await resp.json();
    if (data.ok) {
      setWizardStatus("Tool created.");
      hideWizardConflict();
      if (wizardModal) {
        setTimeout(() => {
          hideWizardModal();
          const refreshButton = wizardEl("refresh");
          if (refreshButton) refreshButton.click();
        }, 600);
      }
      return;
    }
    if (data.status === "conflict") {
      showWizardConflict(data.message, data.suggested);
      setWizardStatus("Resolve conflict to continue.", true);
      return;
    }
    if (data.error) {
      setWizardStatus(data.error, true);
      return;
    }
    setWizardStatus("Tool wizard failed.", true);
  } catch (err) {
    setWizardStatus("Tool wizard failed.", true);
  }
}

async function requestWizardPreview(payload) {
  setWizardStatus("Building preview...");
  try {
    const resp = await fetch("/api/tool-wizard", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, preview: true }),
    });
    const data = await resp.json();
    if (data.ok && data.status === "preview") {
      const preview = data.preview || {};
      const stub = preview.stub || {};
      const binding = preview.binding || {};
      const lines = [];
      lines.push(preview.tool_block || "");
      lines.push("");
      lines.push(`binding: ${binding.entry || "(unknown)"}`);
      lines.push(`stub: ${stub.path || "(unknown)"}`);
      setWizardPreview(lines.join("\n"));
      wizardHasPreview = true;
      if (data.conflicts && data.conflicts.length) {
        showWizardConflict("Conflicts detected. Choose reuse or rename to continue.", data.suggested);
        setWizardStatus("Preview ready (conflicts found).", true);
      } else {
        hideWizardConflict();
        setWizardStatus("Preview ready.");
      }
      return;
    }
    if (data.error) {
      setWizardStatus(data.error, true);
      return;
    }
    setWizardStatus("Preview failed.", true);
  } catch (err) {
    setWizardStatus("Preview failed.", true);
  }
}

function buildWizardPayload() {
  const toolName = wizardEl("toolWizardName").value.trim();
  const purity = wizardEl("toolWizardPurity").value.trim();
  const timeoutValue = wizardEl("toolWizardTimeout").value.trim();
  const inputFields = wizardEl("toolWizardInput").value;
  const outputFields = wizardEl("toolWizardOutput").value;
  if (!toolName || !purity) {
    setWizardStatus("Tool name and purity are required.", true);
    return null;
  }
  return {
    tool_name: toolName,
    purity,
    timeout_seconds: timeoutValue || null,
    input_fields: inputFields || "",
    output_fields: outputFields || "",
  };
}

if (wizardButton) wizardButton.onclick = showWizardModal;
if (wizardClose) wizardClose.onclick = hideWizardModal;
if (wizardCancel) wizardCancel.onclick = hideWizardModal;
if (wizardModal) {
  wizardModal.addEventListener("click", (e) => {
    if (e.target === wizardModal) hideWizardModal();
  });
}
if (wizardForm) {
  wizardForm.addEventListener("submit", (e) => {
    e.preventDefault();
    submitWizard();
  });
}
if (wizardUseSuggestion) {
  wizardUseSuggestion.addEventListener("click", () => {
    if (!wizardSuggestion) return;
    if (wizardSuggestion.tool_name) wizardEl("toolWizardName").value = wizardSuggestion.tool_name;
    wizardHasPreview = false;
    wizardReuse = false;
    submitWizard();
  });
}
if (wizardReuseExisting) {
  wizardReuseExisting.addEventListener("click", () => {
    wizardReuse = true;
    submitWizard();
  });
}
if (wizardPreviewButton) {
  wizardPreviewButton.addEventListener("click", async () => {
    const payload = buildWizardPayload();
    if (!payload) return;
    await requestWizardPreview(payload);
  });
}

if (wizardForm) {
  const inputs = wizardForm.querySelectorAll("input, textarea, select");
  inputs.forEach((input) => {
    input.addEventListener("input", () => {
      markPreviewStale();
    });
  });
}
