const THEME_TOKEN_DEFAULTS = {
  primary_color: "#2563EB",
  secondary_color: "#5856D6",
  background_color: "#FFFFFF",
  foreground_color: "#111827",
  font_family: "Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
  font_size_base: 14,
  font_weight: 500,
  spacing_scale: 1.0,
  border_radius: 10,
  shadow_level: 1,
  surface: "default",
  text: "default",
  muted: "muted",
  border: "default",
  accent: "primary",
};
function resolveThemeTokens(setting, tokens) {
  const merged = { ...THEME_TOKEN_DEFAULTS, ...(tokens || {}) };
  if (typeof merged.font_size_base !== "number") merged.font_size_base = Number(merged.font_size_base) || THEME_TOKEN_DEFAULTS.font_size_base;
  if (typeof merged.font_weight !== "number") merged.font_weight = Number(merged.font_weight) || THEME_TOKEN_DEFAULTS.font_weight;
  if (typeof merged.spacing_scale !== "number") merged.spacing_scale = Number(merged.spacing_scale) || THEME_TOKEN_DEFAULTS.spacing_scale;
  if (typeof merged.border_radius !== "number") merged.border_radius = Number(merged.border_radius) || THEME_TOKEN_DEFAULTS.border_radius;
  if (typeof merged.shadow_level !== "number") merged.shadow_level = Number(merged.shadow_level) || THEME_TOKEN_DEFAULTS.shadow_level;
  return merged;
}
