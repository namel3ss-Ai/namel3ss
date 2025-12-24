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

let wizardSuggestion = null;

function setWizardStatus(message, isError = false) {
  if (!wizardStatus) return;
  wizardStatus.textContent = message || "";
  wizardStatus.style.color = isError ? "#b00020" : "#333";
}

function showWizardModal() {
  if (!wizardModal) return;
  wizardModal.classList.remove("hidden");
  setWizardStatus("");
  hideWizardConflict();
}

function hideWizardModal() {
  if (!wizardModal) return;
  wizardModal.classList.add("hidden");
  setWizardStatus("");
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
  setWizardStatus("Generating tool...");
  try {
    const resp = await fetch("/api/tool-wizard", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
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

function buildWizardPayload() {
  const toolName = wizardEl("toolWizardName").value.trim();
  const moduleName = wizardEl("toolWizardModule").value.trim();
  const functionName = wizardEl("toolWizardFunction").value.trim();
  const purity = wizardEl("toolWizardPurity").value.trim();
  const timeoutValue = wizardEl("toolWizardTimeout").value.trim();
  const inputFields = wizardEl("toolWizardInput").value;
  const outputFields = wizardEl("toolWizardOutput").value;
  if (!toolName || !moduleName || !functionName || !purity) {
    setWizardStatus("Tool name, module name, function name, and purity are required.", true);
    return null;
  }
  return {
    tool_name: toolName,
    module_name: moduleName,
    function_name: functionName,
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
    if (wizardSuggestion.module_name) wizardEl("toolWizardModule").value = wizardSuggestion.module_name;
    submitWizard();
  });
}
