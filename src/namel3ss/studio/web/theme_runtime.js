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

const THEME_VAR_MAP = {
  primary_color: "--n3-primary-color",
  secondary_color: "--n3-secondary-color",
  background_color: "--n3-background-color",
  foreground_color: "--n3-foreground-color",
  font_family: "--n3-font-family",
  font_size_base: "--n3-font-size-base",
  font_weight: "--n3-font-weight",
  spacing_scale: "--n3-spacing-scale",
  border_radius: "--n3-border-radius",
};

let _activeThemeCssHash = "";
let _activeThemeFontUrl = "";

function _ensureThemeStyleTag() {
  let styleTag = document.getElementById("n3ThemeCss");
  if (!styleTag) {
    styleTag = document.createElement("style");
    styleTag.id = "n3ThemeCss";
    document.head.appendChild(styleTag);
  }
  return styleTag;
}

function _applyThemeCss(cssText, cssHash) {
  const nextHash = cssHash || "";
  if (nextHash === _activeThemeCssHash) return;
  const styleTag = _ensureThemeStyleTag();
  styleTag.textContent = typeof cssText === "string" ? cssText : "";
  _activeThemeCssHash = nextHash;
}

function _applyThemeFont(fontUrl) {
  const next = typeof fontUrl === "string" ? fontUrl : "";
  if (next === _activeThemeFontUrl) return;
  const existing = document.getElementById("n3ThemeFont");
  if (!next) {
    if (existing && existing.parentNode) {
      existing.parentNode.removeChild(existing);
    }
    _activeThemeFontUrl = "";
    return;
  }
  let link = existing;
  if (!link) {
    link = document.createElement("link");
    link.id = "n3ThemeFont";
    link.rel = "stylesheet";
    link.onerror = () => {
      if (typeof console !== "undefined" && typeof console.warn === "function") {
        console.warn(`Theme font failed to load: ${next}`);
      }
      if (typeof window !== "undefined" && typeof window.dispatchEvent === "function") {
        window.dispatchEvent(new CustomEvent("n3-theme-font-warning", { detail: { font_url: next } }));
      }
    };
    document.head.appendChild(link);
  }
  link.href = next;
  _activeThemeFontUrl = next;
}

function applyThemeTokens(tokens, settingOverride) {
  const resolved = resolveThemeTokens(settingOverride || runtimeTheme || themeSetting, tokens);
  const body = document.body;
  Object.entries(resolved).forEach(([k, v]) => {
    const safeKey = String(k)
      .replace(/[^a-zA-Z0-9_-]/g, "_")
      .replace(/^_+/, "");
    body.dataset[`theme${safeKey.charAt(0).toUpperCase() + safeKey.slice(1)}`] = v;
    const cssVarName = THEME_VAR_MAP[k];
    if (!cssVarName) return;
    if (k === "font_size_base" || k === "border_radius") {
      document.documentElement.style.setProperty(cssVarName, `${v}px`);
      return;
    }
    document.documentElement.style.setProperty(cssVarName, `${v}`);
  });
  return resolved;
}

function applyThemeBundle(theme) {
  const bundle = theme || {};
  const setting = bundle.current || bundle.setting || runtimeTheme || themeSetting;
  applyTheme(setting);
  applyThemeTokens(bundle.tokens || {}, setting);
  _applyThemeCss(bundle.css || "", bundle.css_hash || "");
  _applyThemeFont(bundle.font_url || "");
}
