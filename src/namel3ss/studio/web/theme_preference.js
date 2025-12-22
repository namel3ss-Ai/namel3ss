function updateRuntimeTheme(value, persistMode) {
  const payload = { value, persist: persistMode };
  fetch("/api/theme", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
    .then((res) => res.json())
    .then((data) => {
      if (!data || data.ok === false) {
        showToast(data && data.error ? data.error : "Theme update failed");
        return;
      }
      if (persistMode === "local" && cachedSummary && cachedSummary.file) {
        try {
          localStorage.setItem(`n3-theme-${cachedSummary.file}`, value);
        } catch (e) {} // eslint-disable-line no-empty
      }
      if (data.ui) {
        cachedManifest = data.ui;
        runtimeTheme = (data.ui.theme && data.ui.theme.current) || value;
        renderUI(data.ui);
      }
      if (data.traces) {
        renderTraces(data.traces);
      }
      renderSummary(cachedSummary);
      renderTruthBar(cachedManifest);
      reselectElement();
    })
    .catch(() => showToast("Theme update failed"));
}

function applyLocalPreferenceIfNeeded() {
  if (!preferencePolicy.allow_override || preferencePolicy.persist !== "local") return;
  if (!cachedSummary || !cachedSummary.file) return;
  try {
    const saved = localStorage.getItem(`n3-theme-${cachedSummary.file}`);
    if (saved && saved !== runtimeTheme && ["light", "dark", "system"].includes(saved)) {
      updateRuntimeTheme(saved, "local");
    }
  } catch (e) {} // eslint-disable-line no-empty
}
