const THEME_TOKEN_DEFAULTS = {
  surface: "default",
  text: "default",
  muted: "muted",
  border: "default",
  accent: "primary",
};
function resolveThemeTokens(setting, tokens) {
  const merged = { ...THEME_TOKEN_DEFAULTS, ...(tokens || {}) };
  return merged;
}
