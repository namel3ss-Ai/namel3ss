(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});

  const CONFIG_CATEGORIES = new Set(["provider_misconfigured", "provider_mock_active", "auth_missing", "auth_invalid"]);

  function renderRuntimeErrorElement(el) {
    const wrapper = document.createElement("div");
    const category = normalizeText(el && el.category, "runtime_internal");
    const severity = normalizeSeverity(el && el.severity, category);
    wrapper.className = `ui-element ui-runtime-error is-${severity}`;

    const header = document.createElement("div");
    header.className = "ui-runtime-error-header";

    const title = document.createElement("div");
    title.className = "ui-runtime-error-title";
    title.textContent = severity === "warn" ? "Runtime warning" : "Runtime error";
    header.appendChild(title);

    const badge = document.createElement("span");
    badge.className = `ui-runtime-error-badge is-${severity}`;
    badge.textContent = category;
    header.appendChild(badge);

    wrapper.appendChild(header);

    const message = document.createElement("div");
    message.className = "ui-runtime-error-message";
    message.textContent = normalizeText(el && el.message, "Runtime request failed.");
    wrapper.appendChild(message);

    const hint = normalizeText(el && el.hint, "");
    if (hint) {
      const hintNode = document.createElement("div");
      hintNode.className = "ui-runtime-error-hint";
      hintNode.textContent = hint;
      wrapper.appendChild(hintNode);
    }

    const meta = document.createElement("div");
    meta.className = "ui-runtime-error-meta";
    const origin = normalizeText(el && el.origin, "runtime");
    const stableCode = normalizeText(el && el.stable_code, "runtime.runtime_internal");
    meta.textContent = `origin: ${origin} · code: ${stableCode}`;
    wrapper.appendChild(meta);

    const diagnostics = normalizeDiagnostics(el && el.diagnostics);
    if (diagnostics.length) {
      const label = document.createElement("div");
      label.className = "ui-runtime-error-diagnostics-label";
      label.textContent = "Additional diagnostics";
      wrapper.appendChild(label);

      const list = document.createElement("ul");
      list.className = "ui-runtime-error-diagnostics";
      diagnostics.forEach((entry) => {
        const item = document.createElement("li");
        item.className = "ui-runtime-error-diagnostic";
        const code = document.createElement("span");
        code.className = "ui-runtime-error-diagnostic-code";
        code.textContent = entry.stable_code;
        item.appendChild(code);
        const text = document.createElement("span");
        text.className = "ui-runtime-error-diagnostic-message";
        text.textContent = `${entry.category}: ${entry.message}`;
        item.appendChild(text);
        list.appendChild(item);
      });
      wrapper.appendChild(list);
    }

    return wrapper;
  }

  function normalizeSeverity(value, category) {
    if (value === "warn" || value === "error") return value;
    if (CONFIG_CATEGORIES.has(category)) return "warn";
    return "error";
  }

  function normalizeDiagnostics(value) {
    if (!Array.isArray(value)) return [];
    const diagnostics = [];
    const seen = new Set();
    value.forEach((entry) => {
      if (!entry || typeof entry !== "object") return;
      const category = normalizeText(entry.category, "");
      const message = normalizeText(entry.message, "");
      const stable_code = normalizeText(entry.stable_code, "");
      if (!category || !message || !stable_code || seen.has(stable_code)) return;
      seen.add(stable_code);
      diagnostics.push({ category, message, stable_code });
    });
    return diagnostics;
  }

  function normalizeText(value, fallback) {
    if (typeof value !== "string") return fallback;
    const text = value.trim();
    return text || fallback;
  }

  root.renderRuntimeErrorElement = renderRuntimeErrorElement;
})();
