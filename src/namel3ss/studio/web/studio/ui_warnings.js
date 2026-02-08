(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const uiWarnings = root.uiWarnings || (root.uiWarnings = {});

  function normalizeManifestWarnings() {
    const manifest = state && typeof state.getCachedManifest === "function" ? state.getCachedManifest() : null;
    const warnings = manifest && Array.isArray(manifest.warnings) ? manifest.warnings : [];
    const rows = warnings
      .filter((item) => item && typeof item === "object")
      .map((item) => ({
        code: String(item.code || ""),
        message: String(item.message || ""),
        fix: item.fix ? String(item.fix) : "",
        path: item.path ? String(item.path) : "",
        line: Number.isInteger(item.line) ? item.line : null,
        column: Number.isInteger(item.column) ? item.column : null,
        category: item.category ? String(item.category) : "general",
      }));
    rows.sort((left, right) => {
      const leftKey = `${left.code}|${left.path}|${left.line || 0}|${left.column || 0}|${left.message}`;
      const rightKey = `${right.code}|${right.path}|${right.line || 0}|${right.column || 0}|${right.message}`;
      return leftKey.localeCompare(rightKey);
    });
    return rows;
  }

  function formatWarningLocation(warning) {
    const chunks = [];
    if (warning.path) chunks.push(warning.path);
    if (warning.line) {
      const col = warning.column ? `:${warning.column}` : "";
      chunks.push(`${warning.line}${col}`);
    }
    return chunks.join(" @ ");
  }

  function buildWarningsCard(warnings, helpers) {
    const buildDetailRow = helpers && typeof helpers.buildDetailRow === "function" ? helpers.buildDetailRow : null;
    const copyText = helpers && typeof helpers.copyText === "function" ? helpers.copyText : null;
    if (!buildDetailRow || !copyText) {
      return document.createElement("div");
    }

    const card = document.createElement("div");
    card.className = "error-card warning-card";

    const header = document.createElement("div");
    header.className = "error-card-header";
    const title = document.createElement("div");
    title.className = "error-card-title";
    title.textContent = "UI warnings";
    const badge = document.createElement("span");
    badge.className = "error-badge warning-badge";
    badge.textContent = `${warnings.length}`;
    header.appendChild(title);
    header.appendChild(badge);

    const details = document.createElement("div");
    details.className = "error-details";
    warnings.forEach((warning) => {
      const message = warning.message || warning.code || "warning";
      const row = buildDetailRow(`${warning.code || "warning"} [${warning.category || "general"}]`, message);
      details.appendChild(row);
      const location = formatWarningLocation(warning);
      if (location) {
        details.appendChild(buildDetailRow("Where", location));
      }
      if (warning.fix) {
        details.appendChild(buildDetailRow("Fix", warning.fix));
      }
    });

    const actions = document.createElement("div");
    actions.className = "json-actions";
    const copyWarnings = document.createElement("button");
    copyWarnings.type = "button";
    copyWarnings.className = "btn ghost";
    copyWarnings.textContent = "Copy warning JSON";
    copyWarnings.onclick = () => copyText(warnings);
    actions.appendChild(copyWarnings);

    card.appendChild(header);
    card.appendChild(details);
    card.appendChild(actions);
    return card;
  }

  uiWarnings.normalizeManifestWarnings = normalizeManifestWarnings;
  uiWarnings.buildWarningsCard = buildWarningsCard;
})();
