function resolveTheme(setting) {
  if (setting === "light" || setting === "dark") return setting;
  if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }
  return "light";
}

function applyTheme(setting) {
  const effective = resolveTheme(setting);
  const body = document.body;
  body.classList.remove("theme-light", "theme-dark");
  body.classList.add(effective === "dark" ? "theme-dark" : "theme-light");
  return effective;
}

function applyThemeTokens(tokens, settingOverride) {
  const resolved = resolveThemeTokens(settingOverride || runtimeTheme || themeSetting, tokens);
  const body = document.body;
  Object.entries(resolved).forEach(([k, v]) => {
    body.dataset[`theme${k.charAt(0).toUpperCase() + k.slice(1)}`] = v;
  });
  return resolved;
}
