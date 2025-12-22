function renderTruthBar(manifest) {
  const runtimeEl = document.getElementById("truthRuntime");
  const effectiveEl = document.getElementById("truthEffective");
  const persistedEl = document.getElementById("truthPersisted");
  const overrideEl = document.getElementById("truthOverride");
  if (!manifest || !manifest.theme) return;
  const theme = manifest.theme;
  const runtime = theme.current || theme.setting || "system";
  const effective = theme.effective || resolveTheme(runtime);
  const source = theme.source || "app";
  const persisted = theme.persisted_current || "none";
  const overrideActive = !!themeOverride;
  if (runtimeEl) runtimeEl.textContent = `Runtime: ${runtime} (source: ${source})`;
  if (effectiveEl) effectiveEl.textContent = `Effective: ${effective}`;
  if (persistedEl) persistedEl.textContent = `Persisted: ${persisted}`;
  if (overrideEl) {
    overrideEl.textContent = overrideActive ? "Preview override: ON" : "Preview override: OFF";
    overrideEl.classList.toggle("badge", overrideActive);
  }
  const label = document.getElementById("themeLabel");
  if (label) {
    if (!preferencePolicy.allow_override) {
      label.textContent = "Theme (preview only)";
    } else if (preferencePolicy.persist === "local") {
      label.textContent = "Theme (runtime, Studio local preference)";
    } else if (preferencePolicy.persist === "file") {
      label.textContent = "Theme (runtime, persisted)";
    } else {
      label.textContent = "Theme (runtime)";
    }
  }
}
